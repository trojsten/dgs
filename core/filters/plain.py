r"""
A quantity written out as plain text, for the formats that have no TeX to typeset it with.

`siunitx` is how a value reaches the page everywhere else: `(§ v §)` emits
`\qty{3}{\metre\per\second}` and xelatex sets it. A drawing has no such step -- `rsvg-convert`
puts SVG text on the page with a system font -- so the same tag inside an `.svg` prints its own
backslashes. These filters write the value out directly instead, `3 m/s`, which is what the
drawing was holding as a literal before it became a template.

**Only where there is no TeX.** In Markdown, in a `.tikz`, in an `eq:` entry, `siunitx` is better
at this than any string can be: it sets the thin space, keeps the number and its unit on one line,
and matches the rest of the booklet. Reach for `txt` in an `.svg`, in a `.gp` axis label, and
nowhere else.

The unit comes from **pint's own `~P` spec** rather than a table here -- short symbols, Unicode
superscripts for powers, `/` for division and `⋅` for multiplication. A table of our own would
have to carry every unit the sources use and would drift from the registry the values are built
in; pint's comes out of that registry by construction, so a unit that can be computed can be
printed.

Two deliberate differences from a naive `f'{quantity:~P}'`:

- **the magnitude is formatted by us**, through the same `format_float` / `format_general` the
  `|f` and `|g` families use, so `|txt` and `|f` agree about how many figures a value has.
  pint's own would print `3.0 m/s` where every other filter in the repository prints `3`;
- **an exponent becomes a superscript too** -- `6.674e-11` is written `6.674×10⁻¹¹`. The unit's
  powers are already superscripts, and `6.674e-11 m³⋅kg⁻¹⋅s⁻²` reads as two notations bolted
  together.

`\qty{45}{\degree}` is `\ang{45}` in `PhysicsQuantity.__format__`, for the reason a drawing wants
too: an angle is written `45°`, closed up, while every other unit takes a space. A bare degree is
the only case, exactly as there -- `\qty{30}{\degree\per\second}` is a rate, and `30 deg/s`.

A range, a list and a product print the way the booklet prints them, with the separators taken
from `core/latex/siunitx.tex` rather than invented here::

    75 cm – 77 cm          a range      `range-phrase = {\text{ -- }}`, `range-units = repeat`
    1 m, 2 m, 3 m          a list       `list-separator = {\text{,}\allowbreak\ }`
    3 cm × 4 cm × 5 cm     a product

**A range rounds to nearest here, and outward in `__format__`.** The two disagree on purpose, and
it is the one place they do. `__format__` prints `answer-interval.md`, which is the set of answers
a marker accepts: rounding its ends to nearest shrinks that set and turns away correct work, which
is the defect `29/bouncy-v` was fixed for, so each end moves outward to the last place it prints.
Nothing `txt` prints is an answer. A range in a drawing labels a span, and widening it would state
a width nobody measured for a reason that does not apply there.
"""
import numbers as _numbers
from typing import Any

from core.builder.context.quantities import (
    PhysicsQuantity,
    QuantityList,
    QuantityProduct,
    QuantityRange,
)

from .numbers import format_float, format_general

#: pint's "pretty" format spec: `~` picks the short symbol over the full name (`m`, not `meter`)
#: and `P` gives Unicode superscripts, `/` and `⋅`.
UNIT_SPEC = '~P'

#: pint's short symbol for a plane angle, which is the one unit that closes up against its number.
DEGREE = 'deg'

SUPERSCRIPT = str.maketrans('0123456789-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻')

#: The magnitude formatter for each format kind, and the letter that builds its spec.
KINDS = {'f': format_float, 'g': format_general}

#: What goes between the parts of a range, a list and a product. Taken from the siunitx settings
#: in `core/latex/siunitx.tex` rather than chosen here, because this filter's job is to print what
#: the booklet prints: `range-phrase = {\text{ -- }}` is an en dash with spaces around it and
#: `list-separator = {\text{,}\allowbreak\ }` is a comma and a space.
RANGE_PHRASE = ' – '
LIST_SEPARATOR = ', '
PRODUCT_SEPARATOR = ' × '


def superscript_exponent(printed: str) -> str:
    """
    `6.674e-11` becomes `6.674×10⁻¹¹`; a number with no exponent is returned untouched.

    `cut_extra_one` has already turned `1e+15` into `e+15` so that siunitx sets `10^{15}` rather
    than `1 · 10^{15}`, and the same thing is wanted here -- an empty mantissa gives `10¹⁵`, with
    no stray `×` in front of it.
    """
    mantissa, separator, exponent = printed.partition('e')
    if not separator:
        return printed

    sign = '-' if exponent.startswith('-') else ''
    digits = exponent.lstrip('+-').lstrip('0') or '0'
    power = f'10{(sign + digits).translate(SUPERSCRIPT)}'
    return f'{mantissa}×{power}' if mantissa else power


def _scalar(x: PhysicsQuantity, precision: int | None, kind: str) -> str:
    """One quantity, magnitude and unit."""
    magnitude = superscript_exponent(KINDS[kind](x.mag, precision))
    unit = format(x.unit, UNIT_SPEC)

    if unit == DEGREE:
        return f'{magnitude}°'
    return f'{magnitude} {unit}' if unit else magnitude


def _render(x: Any, precision: int | None, kind: str) -> str:
    if isinstance(x, _numbers.Number):
        return superscript_exponent(KINDS[kind](x, precision))

    if isinstance(x, PhysicsQuantity):
        return _scalar(x, precision, kind)

    if isinstance(x, QuantityRange):
        # **Each end rounded to nearest, which is where this deliberately parts company with
        # `__format__`.** That rounds outward, and must: what it prints is `answer-interval.md`,
        # the set of answers a marker accepts, and rounding to nearest shrinks that set and turns
        # away correct work -- the `29/bouncy-v` defect. Nothing `txt` prints is an answer. A
        # range in a drawing is a label on a span, so moving its ends outward would state a
        # width nobody measured, for a reason that does not apply.
        ends = (x.minimum, x.maximum)
        return RANGE_PHRASE.join(_scalar(end, precision, kind) for end in ends)

    if isinstance(x, (QuantityList, QuantityProduct)):
        # `__init__` has already coerced every element to a common unit, so each one carries it:
        # `list-units` and `range-units` are both `repeat` in `core/latex/siunitx.tex`, and the
        # booklet prints `3 cm × 4 cm × 5 cm`.
        separator = LIST_SEPARATOR if isinstance(x, QuantityList) else PRODUCT_SEPARATOR
        return separator.join(_scalar(q, precision, kind) for q in x.qs)

    raise TypeError(f"`txt` renders a quantity, a range, a list, a product or a plain number, "
                    f"not {type(x).__name__}.")


def text(x: Any, precision: int | None = None) -> str:
    """A quantity as plain text, the magnitude in fixed notation: `3 m/s`, `1000 kg/m³`, `45°`."""
    return _render(x, precision, 'f')


def text_general(x: Any, precision: int | None = None) -> str:
    """
    The same, with the magnitude in Python's `g`.

    Worth having rather than leaving to `txt`: fixed notation writes the gravitational constant
    as `0.00000000006674`, which is not a label anybody can read at 7pt.
    """
    return _render(x, precision, 'g')
