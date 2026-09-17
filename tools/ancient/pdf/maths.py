r"""
Decoded maths into the house spelling.

What comes out of the glyph stream is a run of characters with the spacing thrown away --
`s=100km`, `\Delta t=20min` -- because a PDF records where each glyph was put, not what it
meant. Three things have to be put back, and all three are mechanical:

- **quantities**: a number butted against a unit is `\qty{}`, which is how every other volume
  in the repository writes one;
- **spacing** around relations, which TeX supplied from the maths class of each character and
  the decode cannot recover;
- **macro boundaries**, handled upstream in `assemble`.

The unit table is `tools.ancient.units.UNITS`, reused whole -- these are the same authors
writing the same notation as 2007, and a unit it does not know is *reported and left alone*
rather than guessed at, exactly as `units.py` says.
"""

from __future__ import annotations

import re

from tools.ancient.units import UNITS

#: Longest first, so `km` wins over `k` and `km/h` over `km`. Sorting once here is what makes
#: the match greedy in the right direction without a parser.
_BY_LENGTH = sorted(UNITS, key=len, reverse=True)

#: A number, then whatever follows it with no space. `1,5` as well as `1.5`: these booklets
#: are Slovak and write a decimal comma, which `rules.thin_comma` normalises afterwards.
RE_QUANTITY = re.compile(
    r'(?<![\w\\])(\d+(?:[.,]\d+)?)(?=[A-Za-z])([A-Za-z/^{}\\0-9-]+)')

#: Relations get a space either side. Not `-`, which is far more often a sign than a relation,
#: and not `/`, which is a solidus inside a fraction.
RE_RELATION = re.compile(r'\s*([=<>])\s*')

#: A capital delta applied to a variable. **This is a finite difference, not the letter.**
#: `core/latex/math.tex` gives it its own macro alongside `\Diff`, `\PDiff` and `\UDiff`, and
#: the repository writes `\FDiff{t}` everywhere -- phys holds 1036 of them against 22 bare
#: `\Delta`, every one of those a symbol declared in its own right (`19/earth-belt` names a
#: quantity `\Delta`; `20/resistor-range` writes the delta-star transformation).
RE_FINITE_DIFFERENCE = re.compile(r'\\Delta\s*(?=[A-Za-z])(\\?[A-Za-z]+(?:_\{?\w+\}?)?)')


def differences(body: str) -> str:
    r"""
    `\Delta t` -> `\FDiff{t}`.

    Only where a variable follows: a `\Delta` standing alone is the letter, and turning that
    into a finite difference would invent an operator the booklet never wrote.
    """
    return RE_FINITE_DIFFERENCE.sub(lambda m: f'\\FDiff{{{m.group(1)}}}', body)


def _reciprocal(tail: str) -> str | None:
    r"""
    `kmh^{-1}` -> `km/h`, if that is a unit the table knows.

    These booklets write a compound unit with a negative exponent, as TeX does, while
    `units.py` is keyed on the solidus form. Rather than duplicate every entry, the exponent
    is turned back into a division -- and only accepted if the result is *in* the table, so a
    wrong split fails loudly instead of inventing a unit.
    """
    if not tail.endswith('^{-1}'):
        return None
    stem = tail[:-len('^{-1}')]
    for cut in range(len(stem) - 1, 0, -1):
        candidate = f'{stem[:cut]}/{stem[cut:]}'
        if candidate in UNITS:
            return candidate
    return None


def quantities(body: str) -> tuple[str, list[str]]:
    """
    `100km` -> `\\qty{100}{\\kilo\\metre}`, and a report of what was not recognised.

    The unit must follow a number with nothing between: `s=100km` has a `s` that is a variable
    and a `km` that is a unit, and only the adjacency to `100` distinguishes them. That is the
    whole rule, and it is why this is safe to run unattended -- a bare letter is never touched.
    """
    missing: list[str] = []

    def replace(m: re.Match[str]) -> str:
        number, tail = m.group(1), m.group(2)
        unit = tail if tail in UNITS else _reciprocal(tail)
        if unit is not None:
            return f'\\qty{{{number}}}{{{UNITS[unit]}}}'
        missing.append(tail)
        return m.group(0)

    return RE_QUANTITY.sub(replace, body), missing


def spacing(body: str) -> str:
    """
    Put back the space TeX set around a relation.

    The glyph stream has no spaces at all -- a gap is an advance, and an advance around `=` is
    a thin space the typesetter inserted from the character's maths class, not a character.
    So `s=100` has to become `s = 100` here or nowhere.
    """
    return RE_RELATION.sub(r' \1 ', body).strip()


#: Function names TeX sets upright and spaces properly. Written out rather than detected,
#: because a bare `sin` in a formula is three italic variables to LaTeX and looks it.
OPERATORS = ('arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh',
             'sin', 'cos', 'tan', 'cot', 'log', 'ln', 'exp', 'max', 'min')

RE_OPERATOR = re.compile(r'(?<!\\)\b(' + '|'.join(OPERATORS) + r')\b')


def operators(body: str) -> str:
    r"""`tan\alpha` -> `\tan\alpha`. Longest first, so `arctan` is not read as `arc` + `tan`."""
    return RE_OPERATOR.sub(lambda m: '\\' + m.group(1), body)


def tidy(body: str) -> tuple[str, list[str]]:
    """Everything, in the order that matters: quantities, then differences, then spacing."""
    body, missing = quantities(body)
    return spacing(operators(differences(body))), missing


#: `s = 100 km` and nothing else: a single symbol, a relation, a number, a unit. Anything
#: more elaborate is a formula rather than a given quantity, and belongs in the prose as
#: written rather than hoisted into `values:`.
RE_ASSIGNMENT = re.compile(
    r'^(?P<symbol>\\?[A-Za-z]+(?:\s*[A-Za-z])?(?:_\{?\w+\}?)?)'
    r'\s*=\s*'
    r'(?P<magnitude>-?\d+(?:[.,]\d+)?)'
    r'(?P<unit>[A-Za-z/^{}0-9-]+)$')

#: Names the render context already uses; a value may not take one. Mirrors
#: `core.builder.context.context.RESERVED_NAMES`, which is the authority.
RESERVED = {'blocks', 'const', 'eq', 'i18n', 'words'}


def _key(symbol: str) -> str:
    r"""
    A `values:` key from a printed symbol.

    `\FDiff{t}` becomes `dt` and `v_0` becomes `v0`: the key has to be an identifier a Jinja
    tag can name, while the symbol keeps whatever the booklet printed. Keeping the two apart
    is the point -- `errors/28.md` records what happens when a subscript that abbreviates a
    word is confused with one that is declared.
    """
    name = re.sub(r'\\FDiff\{(\w+)\}', r'd\1', symbol)
    name = re.sub(r'[^0-9A-Za-z]', '', name.replace('\\', ''))
    name = (name[0].lower() + name[1:]) if name else 'x'
    return f'{name}_' if name in RESERVED else name


def assignment(body: str) -> tuple[str, str, str, str] | None:
    """
    (key, symbol, magnitude, unit) if this run is a given quantity, else None.

    Only an exact `symbol = number unit` qualifies. That keeps the hoist honest: a quantity
    the statement *gives* goes to `values:`, where changing it changes every place it prints,
    and anything else is left as maths.
    """
    m = RE_ASSIGNMENT.match(body.strip())
    if not m:
        return None
    unit = pint_unit(m.group('unit'))
    if unit is None:
        return None
    symbol = differences(m.group('symbol'))
    return (_key(symbol), symbol, m.group('magnitude').replace(',', '.'), unit)


def pint_unit(tail: str) -> str | None:
    r"""
    The unit string to put in `values:`, or None if it cannot be trusted there.

    **`values:` is read by pint, not by `units.py`.** The two disagree, and silently: the
    booklets write a metre per second as `ms^{-1}`, `units.py` maps that to
    `\metre\per\second` quite correctly -- and pint reads the very same string as **one over
    a millisecond**. A quantity hoisted with that unit would be wrong by nine orders of
    magnitude, would print without complaint and would never be questioned again.

    So the exponent form is rewritten to a solidus first, and whatever comes out is *parsed*
    before it is accepted. A unit that fails is not hoisted at all -- it stays in the prose as
    `\qty{}`, where `units.py`'s macro is right and no pint ever sees it.
    """
    candidate = _reciprocal(tail) or tail
    if not re.fullmatch(r'[A-Za-z]+(?:/[A-Za-z]+)?', candidate):
        return None
    try:
        from core.builder.jinja import ureg
        ureg.Quantity(1, candidate)
    except Exception:
        return None
    return candidate
