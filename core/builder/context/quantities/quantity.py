import math
import numbers
import operator
import re
from typing import Optional, Self, Callable, Union, Any

import numpy as np
import pint
from pint import UnitRegistry as u

from core.filters.hacks import cut_extra_one
from core.utilities.dicts import strict_merge


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

    def _binop(self, other, op: Callable[[Self, Union[Self, numbers.Number, u.Quantity]], Any]) -> Self:
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(op(self._quantity, other._quantity))
        elif isinstance(other, numbers.Number) or isinstance(other, pint.registry.Quantity):
            return PhysicsQuantity(op(self._quantity, other))
        else:
            raise TypeError(f"Cannot perform {op} with {type(other)} ({other})")

    def __add__(self, other):
        return self._binop(other, operator.add)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self._binop(other, operator.sub)

    def __rsub__(self, other):
        return -(self - other)

    def __mul__(self, other):
        return self._binop(other, operator.mul)

    def __rmul__(self, other):
        return self * other

    def __pow__(self, exponent):
        return PhysicsQuantity(self._quantity ** exponent)

    def __truediv__(self, other):
        return self._binop(other, operator.truediv)

    def __rtruediv__(self, other):
        return PhysicsQuantity(other / self._quantity)

    def __mod__(self, other):
        return QuantityRange(self, other)

    def __neg__(self):
        return PhysicsQuantity(-self._quantity)

    def __str__(self):
        return format(self, 'g')

    def __format__(self, fmt):
        """
        Format the quantity as a siunitx command (\\num or \\qty).
        The format spec is forwarded to the underlying magnitude formatting:
        empty spec prints the magnitude with Python's default for its type
        (plain decimal for ints, repr-like for floats), which is usually
        what callers want for verbatim output. Pass 'g', '.3f' etc. for
        specific formatting.
        """
        fragments = self.format_struct(fmt=fmt)
        cmd = fragments['cmd']
        si_extra = self.format_si_extra(self.si_extra)
        magnitude = f"{{{fragments['magnitude']}}}"
        unit = f"{{{fragments['unit']}}}" if fragments['unit'] else ''
        return rf'\{cmd}{si_extra}{magnitude}{unit}'

    def __repr__(self):
        return f"{self.__class__.__name__} ({self._quantity})"

    def __eq__(self, other):
        if isinstance(other, PhysicsQuantity):
            return self._quantity == other.quantity
        else:
            return NotImplemented

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
        return PhysicsQuantity(self._quantity.to_base_units(), symbol=self._symbol, si_extra=self.si_extra)

    def widen(self, value: float) -> "QuantityRange":
        """
        Construct a tolerance range from this quantity:
        ``[(1 - v) * x, (1 + v) * x]``.

        For positive ``x`` the smaller endpoint is ``(1 - v) * x`` and the
        larger is ``(1 + v) * x``. For negative ``x`` the order flips so the
        returned range still has minimum <= maximum.

        ``value`` must be non-negative; pass ``0`` for a degenerate range.
        Values >= 1 are allowed and produce a range that crosses zero
        (e.g. ``100.widen(1.5) -> [-50, 250]``).
        """
        assert value >= 0, f"widen factor must be non-negative, got {value}"
        low = self * (1 - value)
        high = self * (1 + value)
        if self._quantity.magnitude >= 0:
            return QuantityRange(low, high)
        else:
            return QuantityRange(high, low)

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

    def ceil(self):
        return PhysicsQuantity(np.ceil(self._quantity))

    def floor(self):
        return PhysicsQuantity(np.floor(self._quantity))

    def approximate(self, digits: int):
        """
        Return an approximate value of the constant (not just formatted output, but truly rounded).
        This is primarily useful for common rounded values, such as g = 10 m/s^2 or m_e = 9.11e-31 kg.
        Note that this representation might not be exact due to machine precision,
        and will have to be passed through `format` again to render correctly.
        """
        assert digits > 0 and isinstance(digits, int), \
            "Digits must be a positive integer"
        if self._quantity.magnitude == 0:
            logarithm = 1
        else:
            logarithm = math.floor(math.log10(abs(self._quantity.magnitude)))

        precision = digits - logarithm - 1
        magnitude = round(self._quantity.magnitude, precision)
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
        """
        Format a dictionary of si extra attributes as a string inside square brackets.
        If nothing is provided, return an empty string instead.
        """
        siextraf = ', '.join(f'{key}={value}' for key, value in si_extra.items())
        siextraf = f'[{siextraf}]' if len(siextraf) >= 1 else siextraf
        return siextraf

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
        return f'{self:g}'

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
        return rf"{self._symbol} = {self:.{precision}f}"

    def equals_general(self, precision: Optional[int]) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._symbol} = {self:.{precision}g}"


def construct_quantity(magnitude, unit, *, symbol: Optional[str] = None):
    """ Constructor-like function """
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
        self.si_extra = strict_merge(self.minimum.si_extra, self.maximum.si_extra)

        # Try to coerce to the same unit (minimum takes precedence).
        # If it works, fine, if not, let pint raise the appropriate exception.
        self.unit = self.minimum.unit
        self.maximum = self.maximum.to(self.unit)

    def __format__(self, fmt: str):
        minr = self.minimum.format_struct(fmt)
        maxr = self.maximum.format_struct(fmt)

        si_extraf = PhysicsQuantity.format_si_extra(self.si_extra)
        minf = f"{{{minr['magnitude']}}}"
        maxf = f"{{{maxr['magnitude']}}}"

        # Use \numrange for dimensionless quantities, \qtyrange otherwise.
        if minr['unit']:
            cmd = 'qtyrange'
            unitf = f"{{{minr['unit']}}}"
        else:
            cmd = 'numrange'
            unitf = ''
        return rf'\{cmd}{si_extraf}{minf}{maxf}{unitf}'

    def widen(self, value: float) -> Self:
        """
        Return a new range whose width is multiplied by ``(1 + value)``,
        expanded symmetrically around the centre.

        For a range ``[a, b]`` with centre ``c = (a + b) / 2`` and half-width
        ``h = (b - a) / 2``, the result is ``[c - h*(1+v), c + h*(1+v)]``.

        This always widens (never narrows) regardless of sign:
            [1, 3]   widen(0.1) -> [0.9, 3.1]
            [-3, -1] widen(0.1) -> [-3.1, -0.9]
            [-1, 1]  widen(0.5) -> [-1.5, 1.5]

        A degenerate range (a == b) stays degenerate, since its half-width
        is zero. Construct an explicit non-degenerate range first if you
        want a tolerance band around a single value.

        This should be useful for specifying ranges of acceptable results
        in Náboj.
        """
        assert value >= 0, f"widen factor must be non-negative, got {value}"
        centre = (self.minimum + self.maximum) * 0.5
        half_width = (self.maximum - self.minimum) * 0.5 * (1 + value)
        return QuantityRange(centre - half_width, centre + half_width)

    def __str__(self):
        return format(self, 'g')


class QuantityList:
    """
    Represents a list of commensurate quantities.
    """

    def __init__(self,
                 *qs: PhysicsQuantity):
        # First, try to force same units everywhere. If it works, good, if it does not, a pint error will be raised.
        assert len(qs) > 0, \
            f"{self.__class__.__name__} must have at least one quantity"
        self.qs = [q.to(qs[0].unit) for q in qs]

        self.si_extra = strict_merge(*(q.si_extra for q in self.qs))

    def __format__(self, fmt: str):
        fqs = [q.format_struct(fmt) for q in self.qs]
        self.magnitudes = ';'.join([fq['magnitude'] for fq in fqs])

        si_extraf = PhysicsQuantity.format_si_extra(self.si_extra)
        magf = f'{{{self.magnitudes}}}'

        # Use \numlist for dimensionless quantities, \qtylist otherwise.
        if fqs[0]['unit']:
            cmd = 'qtylist'
            unitf = f"{{{fqs[0]['unit']}}}"
        else:
            cmd = 'numlist'
            unitf = ''
        return rf'\{cmd}{si_extraf}{magf}{unitf}'

    def __str__(self):
        return format(self, 'g')
