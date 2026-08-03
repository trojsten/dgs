import math
import numbers
import operator
import re
from collections.abc import Callable
from typing import Any, Self

import numpy as np
import pint
from pint import UnitRegistry as u

from core.filters.hacks import cut_extra_one


class MissingSymbolError(Exception):
    """
    Raised when a quantity is rendered in a form that includes its symbol
    (`equals`, `|ef`, `|eg`, `|af`, `|ag`, ...) but no symbol was ever set.
    Silently printing `None = ...` into a solution is much worse than crashing.
    """
    def __init__(self, quantity, method: str):
        super().__init__(
            f"Cannot render {quantity!r} as `{method}`: no symbol is defined. "
            f"Set one with `alias('x')`, `symbol=` at construction, or use a "
            f"symbol-less filter such as `|nf` / `|ng`."
        )
        self.quantity = quantity
        self.method = method


class PhysicsQuantity:
    """
    Represents a physics quantity for comfortable and reproducible use in calculations and texts.
    """

    def __init__(self,
                 quantity: pint.Quantity | float,
                 *,
                 symbol: str | None = None,
                 si_extra: dict[str, str] | None = None,
                 force_f: bool = False):
        if isinstance(quantity, pint.Quantity):
            self._quantity = quantity
        elif isinstance(quantity, numbers.Number):
            self._quantity = u.Quantity(quantity, '1')
        else:
            raise TypeError(f"Cannot construct a {self.__class__.__qualname__} object from {quantity}")

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

    def _binop(self, other, op: Callable[[Self, Self | numbers.Number | u.Quantity], Any]) -> Self:
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(op(self._quantity, other._quantity))
        elif isinstance(other, (numbers.Number, pint.registry.Quantity)):
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
        from .quantity_range import QuantityRange
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
        """ No setter: PhysicsQuantity is immutable. """
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

    @symbol.setter
    def symbol(self, value: str | None):
        self._symbol = value

    @property
    def sym(self):
        """ Return the internal symbol (shorthand). """
        return self._symbol

    @sym.setter
    def sym(self, value: str | None):
        self._symbol = value

    @property
    def s(self):
        """ Return the internal symbol (shorthand). """
        return self._symbol

    @s.setter
    def s(self, value: str | None):
        self._symbol = value

    def alias(self, symbol: str | None) -> "PhysicsQuantity":
        """ Return an aliased quantity with a symbol """
        return PhysicsQuantity(self._quantity, symbol=symbol, si_extra=self.si_extra, force_f=self.force_f)

    def to(self, what):
        """ Convert a physics quantity unit to another compatible unit. """
        return PhysicsQuantity(self._quantity.to(what), symbol=self._symbol, si_extra=self.si_extra)

    def simplify(self):
        return PhysicsQuantity(self._quantity.to_base_units(), symbol=self._symbol, si_extra=self.si_extra)

    def only_unit(self):
        r""" Return a nicely formatted unit (\unit{...} in siunitx format) """
        fragments = self.format_struct(fmt='g')
        si_extra = self.format_si_extra(self.si_extra)
        unit = f"{{{fragments['unit']}}}" if fragments['unit'] else '{1}'
        return rf'\unit{si_extra}{unit}'

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
        from .quantity_range import QuantityRange
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

    def tan(self):
        return PhysicsQuantity(np.tan(self._quantity))

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

    def _require_symbol(self, method: str) -> str:
        """
        Return the symbol, or raise if there is none. Every rendering that
        prints the symbol must go through this.
        """
        if self._symbol is None:
            raise MissingSymbolError(self, method)
        return self._symbol

    @property
    def equals(self) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._require_symbol('equals')} = {self.full}"

    @property
    def eq(self) -> str:
        """
        Shorthand for `equals`
        """
        return self.equals

    @staticmethod
    def _format_spec(kind: str, precision: int | None) -> str:
        """
        Build a format spec of the requested kind ('f' or 'g'). `None` precision
        means the bare spec, i.e. Python's default for that kind -- the same
        convention as `core.filters.numbers.format_float` / `format_general`.
        """
        return kind if precision is None else f'.{precision}{kind}'

    def equals_float(self, precision: int | None = None) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._require_symbol('equals_float')} = {self:{self._format_spec('f', precision)}}"

    def equals_general(self, precision: int | None = None) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._require_symbol('equals_general')} = {self:{self._format_spec('g', precision)}}"

    def approx_float(self, precision: int | None = None) -> str:
        """
        Full form with symbol and approx sign,
        `<symbol> \\approx <full>`
        """
        return rf"{self._require_symbol('approx_float')} \approx {self:{self._format_spec('f', precision)}}"

    def approx_general(self, precision: int | None = None) -> str:
        """
        Full form with symbol and approx sign,
        `<symbol> \\approx <full>`
        """
        return rf"{self._require_symbol('approx_general')} \approx {self:{self._format_spec('g', precision)}}"


def construct_quantity(magnitude, unit, *, symbol: str | None = None):
    """ Constructor-like function """
    return PhysicsQuantity.construct(magnitude, unit, symbol=symbol)
