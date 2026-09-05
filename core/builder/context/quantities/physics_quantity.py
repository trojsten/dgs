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


class UnknownUnitMacroError(Exception):
    r"""
    Raised when pint's LaTeX output contains a unit macro that DGS cannot render.
    `pint`'s `Lx` format builds the macro from the unit's *full name*, so every
    multi-word unit arrives as an invalid TeX command (`\astronomical_unit`,
    `\nautical_mile`, ...). Emitting one would only fail much later, buried in a
    XeLaTeX log, so we refuse here instead.
    """
    def __init__(self, name: str, unit: str):
        super().__init__(
            f"pint rendered the unit `{name}` as `\\{name}`, which is not valid TeX "
            f"(full unit: `{unit}`). Either express the quantity in units DGS knows "
            f"(e.g. 'm/s' rather than 'mps'), or declare a macro in "
            f"`core/latex/siunitx.tex` and map it in `PhysicsQuantity.PINT_TO_SIUNITX`."
        )
        self.name = name
        self.unit = unit


class PhysicsQuantity:
    """
    Represents a physics quantity for comfortable and reproducible use in calculations and texts.
    """

    #: `pint` unit names whose `Lx` macro is invalid TeX, mapped onto the siunitx
    #: macros DGS declares (`core/latex/siunitx.tex`) or that siunitx ships itself.
    #: Anything not listed raises `UnknownUnitMacroError` -- see `_latex_unit`.
    PINT_TO_SIUNITX = {
        'degree_Celsius': r'\celsius',
        'delta_degree_Celsius': r'\dcelsius',
        'degree_Fahrenheit': r'\fahrenheit',
        'astronomical_unit': r'\au',
        'light_year': r'\lightyear',
        'watt_hour': r'\watthour',
        'revolutions_per_minute': r'\rpm',
        'standard_atmosphere': r'\atmosphere',
        'standard_gravity': r'\gforce',
        'unified_atomic_mass_unit': r'\atomicmass',
        'css_pixel': r'\pixel',
        'metric_ton': r'\tonne',           # siunitx built-in
        'electron_volt': r'\electronvolt',  # siunitx built-in
    }

    #: A `\macro` whose name contains an underscore, i.e. one pint built from a
    #: multi-word unit name. `\kilo\meter_per_hour` matches only the second part.
    _UNDERSCORE_MACRO = re.compile(r'\\([A-Za-z]+(?:_[A-Za-z0-9]+)+)')

    #: pint names two SI units the American way, and only these two: `meter`, 266 times across the
    #: repository's `values:`, and `liter`, 21 times. siunitx declares both spellings of each and
    #: they typeset identically, so this changes no printed page.
    #:
    #: It is about the rendered source, which the sources themselves write in British English
    #: throughout. Before this, a hand-written `\qty{4}{\milli\litre}` and the same quantity taken
    #: from `values:` came out spelled differently, sometimes in one sentence -- and every literal
    #: that becomes a tag turns one `\metre` into a `\meter`, so the mixture spreads as the
    #: migration to computed answers proceeds.
    #:
    #: Separate from `PINT_TO_SIUNITX`, which exists for names that are not valid TeX at all and
    #: raises for anything it does not know. An unlisted spelling here is simply left alone.
    PINT_SPELLING = {
        r'\meter': r'\metre',
        r'\liter': r'\litre',
    }

    #: Any complete `\macro` name, so a spelling is rewritten as a whole word: a bare `str.replace`
    #: would also rewrite the head of a longer name that merely starts the same way.
    _MACRO = re.compile(r'\\[A-Za-z]+')

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

    def __abs__(self):
        return PhysicsQuantity(abs(self._quantity))

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

    def _compare(self, other, op: Callable[[Any, Any], bool]):
        """
        Order two quantities, so that `|max`, `|min` and `sorted` work on them.

        Not routed through `_binop`, which wraps its result in a `PhysicsQuantity`: a comparison
        yields a bool. Incomparable dimensions raise from pint rather than quietly comparing
        magnitudes, which is the point -- `\\qty{1}{\\metre} < \\qty{1}{\\second}` is not false,
        it is meaningless. Different units of the same dimension compare fine, pint converting
        as it goes.
        """
        if isinstance(other, PhysicsQuantity):
            return op(self._quantity, other._quantity)
        elif isinstance(other, (numbers.Number, pint.registry.Quantity)):
            return op(self._quantity, other)
        else:
            return NotImplemented

    def __lt__(self, other):
        return self._compare(other, operator.lt)

    def __le__(self, other):
        return self._compare(other, operator.le)

    def __gt__(self, other):
        return self._compare(other, operator.gt)

    def __ge__(self, other):
        return self._compare(other, operator.ge)

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
        unit = self._latex_unit(si_fragment.group('unit'))

        return {
            'cmd': 'num' if unit == '' else 'qty',
            'si_extra': self.si_extra,
            'magnitude': magnitude,
            'unit': unit,
        }

    @classmethod
    def _latex_unit(cls, unit: str) -> str:
        r"""
        Rewrite pint's multi-word unit macros into the siunitx macros DGS declares.
        Raises `UnknownUnitMacroError` for anything unmapped rather than emitting
        an invalid `\foo_bar`.

        Then put the two units pint spells American into British, to match the sources.
        Multi-word names go first, so a mapping that produces one of them is caught too.
        """
        def substitute(match: re.Match) -> str:
            name = match.group(1)
            if name not in cls.PINT_TO_SIUNITX:
                raise UnknownUnitMacroError(name, unit)
            return cls.PINT_TO_SIUNITX[name]

        unit = cls._UNDERSCORE_MACRO.sub(substitute, unit)
        return cls._MACRO.sub(lambda m: cls.PINT_SPELLING.get(m.group(0), m.group(0)), unit)

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
        Build a format spec of the requested kind ('f', 'g' or 'e'). `None` precision
        means the bare spec, i.e. Python's default for that kind -- the same
        convention as `core.filters.numbers.format_float` / `format_general` /
        `format_exponential`.
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

    def equals_exponential(self, precision: int | None = None) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self._require_symbol('equals_exponential')} = {self:{self._format_spec('e', precision)}}"

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

    def approx_exponential(self, precision: int | None = None) -> str:
        """
        Full form with symbol and approx sign,
        `<symbol> \\approx <full>`
        """
        return rf"{self._require_symbol('approx_exponential')} \approx {self:{self._format_spec('e', precision)}}"


def construct_quantity(magnitude, unit, *, symbol: str | None = None):
    """ Constructor-like function """
    return PhysicsQuantity.construct(magnitude, unit, symbol=symbol)
