import functools
import operator
import math
import numbers
import re
from typing import Optional

import numpy as np
import pint
from pint import UnitRegistry as u

from core.filters.hacks import cut_extra_one


class PhysicsQuantity:
    """
    Represents a physics quantity for comfortable and reproducible use in calculations and texts.
    """

    def __init__(self,
                 quantity: u.Quantity,
                 *,
                 symbol: str = None,
                 si_extra: dict[str, str] = None,
                 force_f: bool = False):
        self._quantity = quantity
        self._symbol = symbol

        self.si_extra = {} if si_extra is None else si_extra
        assert isinstance(self.si_extra, dict), \
            f"si_extra must be a dict[str, str], got {type(self.si_extra)} instead"

        self.force_f = force_f

    @staticmethod
    def construct(magnitude, unit, **kwargs):
        """
        Construct from magnitude and unit.
        """
        return PhysicsQuantity(u.Quantity(magnitude, unit), **kwargs)

    def __add__(self, other):
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(self._quantity + other._quantity)
        elif isinstance(other, numbers.Number):
            return PhysicsQuantity(self._quantity + other)
        else:
            raise TypeError(f"Cannot __add__ with {type(other)} ({other})")

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(self._quantity - other._quantity)
        elif isinstance(other, numbers.Number):
            return PhysicsQuantity(self._quantity - other)
        else:
            raise TypeError(f"Cannot __sub__ with {type(other)} ({other})")

    def __rsub__(self, other):
        return -(self - other)

    def __mul__(self, other):
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(self._quantity * other._quantity)
        elif isinstance(other, numbers.Number):
            return PhysicsQuantity(self._quantity * other)
        else:
            return NotImplemented

    def __rmul__(self, other):
        return self * other

    def __pow__(self, exponent):
        return PhysicsQuantity(self._quantity ** exponent)

    def __truediv__(self, other):
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(self._quantity / other._quantity)
        elif isinstance(other, numbers.Number) or isinstance(other, pint.registry.Quantity):
            return PhysicsQuantity(self._quantity / other)
        else:
            raise TypeError(f"Cannot __truediv__ type {type(other)} ({other})")

    def __rtruediv__(self, other):
        return PhysicsQuantity(other / self._quantity)

    def __xor__(self, other):
        return QuantityRange(self.quantity, other.quantity)

    def __neg__(self):
        return PhysicsQuantity(-self._quantity)

    def __str__(self):
        return self._format()

    def __repr__(self):
        return f"{self.__class__.__name__} ({self._quantity})"

    def __eq__(self, other):
        return self._quantity == other._quantity

    @property
    def quantity(self):
        """ Access the internal attribute """
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        raise TypeError(f"{self.__class__.__name__} ({value}) is immutable")

    @property
    def mag(self):
        """ Return the internal magnitude. """
        return self._quantity.magnitude

    @property
    def unit(self):
        """ Return the internal unit. """
        return self._quantity.units

    @property
    def symbol(self):
        """ Return the internal symbol. """
        return self._symbol

    @property
    def sym(self):
        """ Return the internal symbol (shorthand). """
        return self._symbol

    def to(self, what):
        return PhysicsQuantity(self._quantity.to(what), symbol=self._symbol, si_extra=self.si_extra)

    def simplify(self):
        return PhysicsQuantity(self._quantity.to_base_units())

    def sin(self):
        return PhysicsQuantity(np.sin(self._quantity))

    def cos(self):
        return PhysicsQuantity(np.cos(self._quantity))

    def arcsin(self):
        return PhysicsQuantity(np.arcsin(self._quantity))

    def arctan(self):
        return PhysicsQuantity(np.arctan(self._quantity))

    def arccos(self):
        return PhysicsQuantity(np.arccos(self._quantity))

    def log(self):
        return PhysicsQuantity(np.log(self._quantity))

    def degrees(self):
        return PhysicsQuantity(np.degrees(self._quantity))

    def approximate(self, digits: int):
        """
        Return an approximate value of the constant (not just formatted output, but truly rounded).
        This is primarily useful for common rounded values, such as g = 10 m/s^2 or m_e = 9.11e-31 kg.
        Note that this representation might not be exact due to machine precision,
        and will have to be passed through `format` again to render correctly.
        """
        if self._quantity.magnitude == 0:
            logarithm = 1
        else:
            logarithm = math.floor(math.log10(abs(self._quantity.magnitude)))

        precision = digits - logarithm - 1
        magnitude = math.trunc(self._quantity.magnitude * (10 ** precision) + 0.5) / (10 ** precision)
        return PhysicsQuantity(u.Quantity(magnitude, self._quantity.units), symbol=self._symbol, si_extra=self.si_extra)

    def format_struct(self, fmt: str = 'g'):
        """
        Format the physical quantity to a dict for further processing.
        """
        pint_output = f"{self._quantity:Lx}"
        si_fragment = re.search(r'\\SI\[]{(?P<magnitude>.*)}{(?P<unit>.*)}$', pint_output)
        magnitude = cut_extra_one(f'{self._quantity.magnitude:{fmt}}')
        unit = re.sub(r'\\degree_Celsius', r'\\celsius', si_fragment.group('unit'))
        unit = re.sub(r'\\delta_degree_Celsius', r'\\dcelsius', unit)

        return {
            'cmd': 'num' if unit == '' else 'qty',
            'si_extra': self.si_extra,
            'magnitude': magnitude,
            'unit': unit,
        }

    @staticmethod
    def format_si_extra(si_extra) -> str:
        siextraf = ', '.join(f'{key}={value}' for key, value in si_extra)
        siextraf = f'[{siextraf}]' if len(siextraf) >= 1 else siextraf
        return siextraf

    def _format(self, fmt: str = 'g'):
        """Return a formatted string representation, by default a `g` one."""
        fragments = self.format_struct(fmt=fmt)
        cmd = fragments['cmd']
        si_extra = self.format_si_extra(self.si_extra)
        magnitude = f'{{{fragments['magnitude']}}}'
        unit = '' if fragments['unit'] is None else f'{{{fragments['unit']}}}'
        return rf'\{cmd}{si_extra}{magnitude}{unit}'

    @property
    def full(self):
        r"""
        Property for full, default-formatted values.
        Use as (* const.name.full *). This will render
        ```
        constant:
            value: 1.2345e-6
            unit: "\\kilo\\gram"
            digits: 3
        ```
        as \qty{1.23e-6}{\kilo\gram}.
        """
        return self._format()

    def fullf(self, precision: int = None) -> str:
        """
        Full, with f formatting
        """
        if precision is None:
            precision = self.digits
        return self._format(f'.{precision}f')

    def fullg(self, precision: int = None) -> str:
        """
        Full, with f formatting
        """
        if precision is None:
            precision = self.digits
        return self._format(f'.{precision}g')

    @property
    def equals(self) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._symbol} = {self.full}"

    @property
    def eq(self) -> str:
        """
        Shorthand for `equals`
        """
        return self.equals

    def equals_float(self, precision: Optional[int]) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._symbol} = {self._format(f'.{precision}f')}"

    def equals_general(self, precision: Optional[int]) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._symbol} = {self._format(f'.{precision}g')}"


def construct_quantity(magnitude, unit, *, symbol: Optional[str] = None):
    return PhysicsQuantity.construct(magnitude, unit, symbol=symbol)


class QuantityRange:
    """
    Represents a range of two magnitudes of commensurate quantities.
    Primarily meant to be useful for result tolerances.
    """

    def __init__(self,
                 minimum: PhysicsQuantity,
                 maximum: PhysicsQuantity):
        self.minimum = minimum
        self.maximum = maximum
        self.si_extra = self.minimum.si_extra | self.maximum.si_extra

        assert self.minimum.unit == self.maximum.unit, \
            (f"Ranges can only be constructed from quantities with commensurate units,"
             f"but got {self.minimum.unit} and {self.maximum.unit}")
        self.unit = self.minimum.unit


    def __str__(self):
        minr = self.minimum.format_struct()
        maxr = self.maximum.format_struct()

        si_extra = PhysicsQuantity.format_si_extra(self.si_extra)
        minf = f'{{{minr['magnitude']}}}'
        maxf = f'{{{maxr['magnitude']}}}'
        unitf = f'{{{minr["unit"]}}}'

        cmd = 'qtyrange'
        return rf'\{cmd}{siextraf}{minf}{maxf}{unitf}'


class QuantityList:
    """
    Represents a list of commensurate quantities.
    """

    def __init__(self,
                 *qs: PhysicsQuantity):
        self.qs = qs
        self.si_extra = functools.reduce(operator.or_, [q.si_extra for q in self.qs])

        unique_units = set([q.unit for q in self.qs])
        assert len(unique_units) == 1, \
            f"Lists can only be constructed from a list of commensurate quantities, got {unique_units}"

    def __str__(self):
        cmd = 'qtylist'
        fqs = [q.format_struct() for q in self.qs]
        self.magnitudes = ';'.join([fq['magnitude'] for fq in fqs])

        unitf = f'{{{fqs[0]['unit']}}}'
        siextraf = ', '.join(f'{key}={value}' for key, value in self.si_extra)
        siextraf = f'[{siextraf}]' if len(siextraf) >= 1 else siextraf
        magf = f'{{{self.magnitudes}}}'

        return rf'\{cmd}{siextraf}{magf}{unitf}'

