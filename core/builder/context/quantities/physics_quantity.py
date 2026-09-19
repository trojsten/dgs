import math
import numbers
import operator
import re
from collections.abc import Callable
from typing import Any, Self

import numpy as np
import pint
from pint import UnitRegistry as u

from core.filters.hacks import BareKind, cut_extra_one, natural


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

    #: Significant figures for the rounded renderings -- `apx`, and `PhysicsConstant`'s own
    #: `approx`, `format` and `full*`. Three is the constants sheet's usual precision and so
    #: the sensible default for a computed value, which is what most quantities carrying this
    #: are; a constant overrides it from `constants.yaml`.
    DEFAULT_DIGITS = 3

    #: How far the printed figures may sit from the stored magnitude and still count as the
    #: whole truth. Nine orders of magnitude separate the two populations across the sources --
    #: a value that prints exactly lands within a handful of ulps (`29/coil-kirchhoff` solves a
    #: 3x3 system and comes out 6 from an exact 0.1 A), while one that is genuinely rounded is
    #: out by 10^9 -- so anything in the wide middle works and this is not a tuned number.
    ULP_TOLERANCE = 1000

    def __init__(self,
                 quantity: pint.Quantity | float,
                 *,
                 symbol: str | None = None,
                 si_extra: dict[str, str] | None = None,
                 force_f: bool = False,
                 digits: int = DEFAULT_DIGITS,
                 exact: bool = True):
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
        self.digits = digits
        #: Whether the stored magnitude is the true value, as against a measured or rounded
        #: stand-in for it. A number a statement *gives* is exact -- `s = 100 km` is not
        #: approximately anything -- so that is the default, and `ConstantsContext` overrides it
        #: for `constants.yaml`, where a value is measured unless it declares `exact: true`.
        #:
        #: It spreads as contamination only, never as a guarantee: see `_binop`.
        self.exact = exact

    @staticmethod
    def construct(magnitude, unit, **kwargs):
        r"""
        Construct from a magnitude and a unit.

        **Idempotent in the magnitude.** `PQ` of something that is already a quantity
        re-expresses it in `unit` instead of wrapping it a second time. The second wrap used to
        be invisible until it reached the page -- `PQ(PQ(0.4, ''), '')` printed
        `\num{\num{0.4}}`, which siunitx cannot parse, and the natural spelling of an angle,
        `PQ(acos(x), 'radian').to('degree')`, printed `\qty{\qty{32.53}{\radian}}{\degree}`.
        Both get as far as the TeX and fail there, a long way from the `derived:` line that
        wrote them, and the workaround was to remember `.mag` at every call site.

        The conversion is pint's, so an incompatible unit raises exactly as it always did:
        `PQ(length, 'second')` is a mistake however it is spelled. Radians are dimensionless to
        pint, which is what lets `PQ(acos(x), 'radian')` take either a float or a bare number
        and mean the same thing.

        What the quantity already carries -- its symbol, digits, `si_extra` and `exact` -- comes
        with it, and an explicit keyword here overrides that, so `PQ(q, 'degree', symbol=r'\beta')`
        renames it.
        """
        if isinstance(magnitude, PhysicsQuantity):
            carried = {'symbol': magnitude._symbol, 'si_extra': magnitude.si_extra,
                       'force_f': magnitude.force_f, 'digits': magnitude.digits,
                       'exact': magnitude.exact}
            return PhysicsQuantity(magnitude._quantity.to(unit), **(carried | kwargs))
        if isinstance(magnitude, pint.Quantity):
            return PhysicsQuantity(magnitude.to(unit), **kwargs)
        return PhysicsQuantity(u.Quantity(magnitude, unit), **kwargs)

    def _binop(self, other, op: Callable[[Self, Self | numbers.Number | u.Quantity], Any]) -> Self:
        """
        Arithmetic on the magnitudes, dropping the symbol -- a product of two quantities is not
        either of them -- and carrying `exact` forward as contamination.

        **Contamination only.** A result of two exact operands is *not* thereby exact: dividing
        an exact 100 km by an exact 3 h gives 33.333..., which no decimal string holds. What
        saves that case is the other half of the test, in `prints_exactly`, which asks whether
        the figures actually printed come back to the stored magnitude. So `exact` answers "is
        this value the true one" and the round-trip answers "are these figures all of it",
        and `equals` needs both.

        That division is why the flag cannot propagate the other way round, and `numpy` is why
        it must not try: `np.sin` builds its result straight from the constructor without ever
        reaching here, so a rule that inferred exactness from its operands would quietly call
        `sin(20 deg)` exact. Under contamination it defaults to exact and the round-trip catches
        it -- 2.6 billion ulps out -- while `sin(30 deg)` is exactly 0.5 and prints as `=`.
        """
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(op(self._quantity, other._quantity),
                                   exact=self.exact and other.exact)
        elif isinstance(other, (numbers.Number, pint.registry.Quantity)):
            return PhysicsQuantity(op(self._quantity, other), exact=self.exact)
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
        r"""
        Raise to a power, which may itself be a dimensionless quantity.

        An exponent has to be a pure number -- pint says so and it is right, since `x` to the
        power of 3 kg means nothing. But a `values:` entry with `unit: ~` *is* a pure number and
        arrives here wrapped, so `ratio**((kappa - 1) / kappa)` with kappa declared at 1.4 used
        to fail with `Cannot power UnitsContainer by PhysicsQuantity` -- a message naming neither
        the quantity nor the `derived:` line, and fixed only by remembering `.mag` on every
        appearance of kappa. Unwrapping a dimensionless exponent here says the same thing the
        author meant. Anything with a dimension still raises, from pint, as before.
        """
        if isinstance(exponent, PhysicsQuantity):
            exponent = exponent._quantity
        if isinstance(exponent, pint.Quantity):
            exponent = exponent.to('').magnitude
        return PhysicsQuantity(self._quantity ** exponent, exact=self.exact)

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
        # An angle on its own is `\ang`, siunitx's own command for one, and what the sources
        # write by hand throughout. Only here: there is no `\anglist` or `\angrange`, so a list
        # or a range of angles stays `\qtylist` / `\qtyrange` and keeps `\degree` as its unit.
        # Only a bare degree, too -- `\qty{30}{\degree\per\second}` is a rate, not an angle.
        if fragments['unit'] == r'\degree':
            return rf'\ang{si_extra}{magnitude}'
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
        return PhysicsQuantity(self._quantity, symbol=symbol, si_extra=self.si_extra,
                               force_f=self.force_f, digits=self.digits, exact=self.exact)

    def to(self, what):
        """ Convert a physics quantity unit to another compatible unit. """
        return PhysicsQuantity(self._quantity.to(what), symbol=self._symbol, si_extra=self.si_extra,
                               digits=self.digits, exact=self.exact)

    def simplify(self):
        return PhysicsQuantity(self._quantity.to_base_units(), symbol=self._symbol,
                               si_extra=self.si_extra, digits=self.digits, exact=self.exact)

    def only_unit(self):
        r""" Return a nicely formatted unit (\unit{...} in siunitx format) """
        fragments = self.format_struct(fmt='g')
        si_extra = self.format_si_extra(self.si_extra)
        unit = f"{{{fragments['unit']}}}" if fragments['unit'] else '{1}'
        return rf'\unit{si_extra}{unit}'

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

    def round(self):
        """
        Nearest whole multiple of the unit, the third of the trio with `ceil` and `floor`.

        `20/equinox` rounds an arc length to tens of kilometres, which is
        `round(d.to('kilometre') / 10) * 10` -- and there was no `round` to write it with.
        """
        return PhysicsQuantity(np.round(self._quantity))

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
        # Never exact: rounding is the whole point of this method, so `const.g.approx` is 10
        # and says so. A `result_approx` computed from it inherits that, which is correct.
        return PhysicsQuantity(u.Quantity(magnitude, self._quantity.units), symbol=self._symbol,
                               si_extra=self.si_extra, digits=self.digits, exact=False)

    def format_struct(self, fmt: str = 'g'):
        """
        Format the physical quantity to a dict for further processing.
        """
        pint_output = f"{self._quantity:Lx}"
        si_fragment = re.search(r'\\SI\[]{(?P<magnitude>.*)}{(?P<unit>.*)}$', pint_output)
        # A bare `f` or `e` means Python's six decimal places, which is a precision the
        # caller did not ask for and `1e-8` does not survive. See `natural`.
        magnitude = cut_extra_one(natural(self._quantity.magnitude, fmt)
                                  if BareKind.match(fmt or '')
                                  else f'{self._quantity.magnitude:{fmt}}')
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

    def _round_trips(self, fmt: str) -> bool:
        """
        Do the figures this format prints come back to the stored magnitude?

        Within `ULP_TOLERANCE`, because the comparison is against a binary float that has been
        through arithmetic: `29/coil-kirchhoff` solves a 3x3 system for a current that is
        exactly 0.1 A and stores 0.10000000000000009, six ulps out. An exact equality test
        calls that rounded, which is what makes the naive version of this check unusable.

        Anything that is not a real number -- an array, a `Decimal`, whatever pint was handed --
        is left alone: this decides between `=` and `\approx`, and for those it declines to.
        """
        magnitude = self._quantity.magnitude
        if isinstance(magnitude, bool) or not isinstance(magnitude, numbers.Real):
            return True
        try:
            stored = float(magnitude)
            shown = float(f'{stored:{fmt}}')
        except (ValueError, TypeError, OverflowError):
            return True
        if shown == stored:
            return True
        if stored == 0 or math.isnan(stored) or math.isinf(stored):
            return False
        return abs(shown - stored) <= self.ULP_TOLERANCE * math.ulp(stored)

    @property
    def prints_exactly(self) -> bool:
        r"""
        Whether `equals` may write `=`: the value has to be the true one *and* the figures it
        prints have to be all of it.

        Two independent failures, and each catches what the other cannot. `const.speed_sound` is
        343 m/s, which prints back exactly and is still not the speed of sound -- only the
        declaration knows that. `sqrt(2)` is exact by every declaration on its way here and
        prints as 1.41421 -- only the round-trip knows that.
        """
        return self.exact and self._round_trips('g')

    @property
    def equals(self) -> str:
        r"""
        Full form with symbol and the relation the value has earned:
        `<symbol> = <full>` where the printed figures are the whole truth,
        `<symbol> \approx <full>` where they are not.

        `approximately` is the same thing said outright, and at `digits` rather than `%g`.
        """
        relation = '=' if self.prints_exactly else r'\approx'
        return rf"{self._require_symbol('equals')} {relation} {self.full}"

    @property
    def eq(self) -> str:
        """
        Shorthand for `equals`
        """
        return self.equals

    @property
    def approximately(self) -> str:
        r"""
        Full form with symbol and an approximation sign, at `digits` significant figures:
        `<symbol> \approx <value>`.

        `equals` reaches for `\approx` on its own where the value has earned it, so this is for
        saying so outright -- and for the precision, which is `digits` rather than `%g`'s six.
        `equals` prints what it has; `approximately` says "to this many figures".

        The value is *rounded* and then printed, not printed to a precision: `.1g` of 9.80665 is
        `1e+01`, which `cut_extra_one` turns into `\qty{e+01}{}` so siunitx sets it as a bare
        power of ten. Correct, and not what anyone wants to read for `g \approx 10`. Rounding
        first is what `PhysicsConstant.full_approx` already does for the same reason.
        """
        return rf"{self._require_symbol('approximately')} \approx {self.approximate(self.digits):g}"

    @property
    def apx(self) -> str:
        """
        Shorthand for `approximately`
        """
        return self.approximately

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
