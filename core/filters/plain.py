r"""
`|txt`: a quantity written out as plain text, for the formats that have no TeX to typeset it.

`siunitx` is how a value reaches the page everywhere else: `(§ v §)` emits
`\qty{3}{\metre\per\second}` and xelatex sets it. A drawing has no such step -- `rsvg-convert`
puts SVG text on the page with a system font -- so the same tag inside an `.svg` prints its own
backslashes. These filters write the value out directly instead, `3 m/s`, which is what the
drawing was holding as a literal before it became a template.

**Only where there is no TeX.** In Markdown, in a `.tikz`, in an `eq:` entry, `siunitx` is better
at this than any string can be: it sets the thin space, keeps the number and its unit on one line,
and matches the rest of the booklet. Reach for `txt` in an `.svg`, in a `.gp` axis label, and
nowhere else.

**This module used to render quantities itself**, duplicating the type dispatch, the magnitude
formatting, the degree special case and the separators that `core/builder/context/quantities/`
already had. It no longer does: the spelling lives in `backend.py` as `PLAIN`, beside `LATEX`,
and `|txt` is a call that asks for the other one. There is one implementation of "how several
quantities are written", with two spellings, rather than two implementations kept in step by hand.

What that unification fixed, since it is the one output that could have moved: `|txtg` ignored
`force_f`, so a quantity declared never to be written as a power of ten was written as one
anyway. It honours it now, like every other filter. No call site in the repository formats a
`force_f` quantity as text -- `gforce` is the only constant carrying the flag, and the only
source declaring it uses no `|txt` -- so nothing in the corpus moved, which the render gate
confirmed.

Two deliberate differences from a naive `f'{quantity:~P}'`, both now in `PlainBackend`:

- **the magnitude is formatted by us**, through the same path the `|f` and `|g` families use, so
  `|txt` and `|f` agree about how many figures a value has. pint's own would print `3.0 m/s`
  where every other filter in the repository prints `3`;
- **an exponent becomes a superscript too** -- `6.674e-11` is written `6.674×10⁻¹¹`. The unit's
  powers are already superscripts, and `6.674e-11 m³⋅kg⁻¹⋅s⁻²` reads as two notations bolted
  together.

**A range rounds to nearest here, and outward in LaTeX.** The two disagree on purpose, and it is
the one place they disagree about a value rather than a spelling. LaTeX prints
`answer-interval.md`, the set of answers a marker accepts: rounding its ends to nearest shrinks
that set and turns away correct work, which is the defect `29/bouncy-v` was fixed for. Nothing
`txt` prints is an answer. A range in a drawing labels a span, and widening it would state a
width nobody measured. `Backend.rounds_outward` carries it.
"""
import numbers as _numbers
from typing import Any

from core.builder.context.quantities import backend
from core.builder.context.quantities.backend import superscript_exponent

from .numbers import format_float, format_general

#: The magnitude formatter for each format kind, and the letter that builds its spec. Only a bare
#: number reaches these directly; a quantity goes through `__format__`, which uses the same ones.
KINDS = {'f': format_float, 'g': format_general}

#: What `|txt` accepts beside a plain number. Named rather than inferred, so that passing a
#: string or a `MathObject` still fails with a sentence instead of printing something odd.
RENDERABLE = ('PhysicsQuantity', 'QuantityAggregate')

__all__ = ['superscript_exponent', 'text', 'text_general']


def _render(x: Any, precision: int | None, kind: str) -> str:
    if isinstance(x, _numbers.Number):
        return superscript_exponent(KINDS[kind](x, precision))

    from core.builder.context.quantities import PhysicsQuantity, QuantityAggregate
    if not isinstance(x, (PhysicsQuantity, QuantityAggregate)):
        raise TypeError(f"`txt` renders a quantity, a range, a list, a product or a plain "
                        f"number, not {type(x).__name__}.")

    with backend.using(backend.PLAIN):
        return format(x, kind if precision is None else f'.{precision}{kind}')


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
