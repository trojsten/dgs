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
"""
import numbers as _numbers
from typing import Any, Callable

from core.builder.context.quantities import PhysicsQuantity

from .numbers import format_float, format_general

#: pint's "pretty" format spec: `~` picks the short symbol over the full name (`m`, not `meter`)
#: and `P` gives Unicode superscripts, `/` and `⋅`.
UNIT_SPEC = '~P'

#: pint's short symbol for a plane angle, which is the one unit that closes up against its number.
DEGREE = 'deg'

SUPERSCRIPT = str.maketrans('0123456789-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻')


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


def _render(x: Any, precision: int | None, formatter: Callable[[Any, int | None], str]) -> str:
    if isinstance(x, _numbers.Number):
        return superscript_exponent(formatter(x, precision))

    if not isinstance(x, PhysicsQuantity):
        raise TypeError(f"`txt` renders a quantity or a plain number, not {type(x).__name__}. "
                        f"A range, a list or a product has no plain-text spelling yet; print its "
                        f"parts separately, or use `siunitx` if the format can typeset it.")

    magnitude = superscript_exponent(formatter(x.mag, precision))
    unit = format(x.unit, UNIT_SPEC)

    if unit == DEGREE:
        return f'{magnitude}°'
    return f'{magnitude} {unit}' if unit else magnitude


def text(x: Any, precision: int | None = None) -> str:
    """A quantity as plain text, the magnitude in fixed notation: `3 m/s`, `1000 kg/m³`, `45°`."""
    return _render(x, precision, format_float)


def text_general(x: Any, precision: int | None = None) -> str:
    """
    The same, with the magnitude in Python's `g`.

    Worth having rather than leaving to `txt`: fixed notation writes the gravitational constant
    as `0.00000000006674`, which is not a label anybody can read at 7pt.
    """
    return _render(x, precision, format_general)
