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


#: A maths accent is set *over* its symbol, so it reaches the decode as a separate glyph at
#: almost the same x. TeX puts the accent's origin a hair to the *left* of the letter it
#: covers -- `m\vec v` traces as `m`@343.1, the arrow@354.0, `v`@354.5 -- so the glyph after
#: the accent is the one it belongs to, and that rule is applied first.
RE_ACCENT_PREFIX = re.compile(r'\\vec\s*(\\?[A-Za-z]+)')
#: Only for an accent the prefix pass could not place, which happens when the accent ends a
#: row. The `{` in the look-ahead matters as much as the letters: without it this fires again
#: on the `\vec{v}` the prefix pass just wrote and takes the `m` in front of it as well. Running this as one alternation with the rule above gets `m\vec v` wrong: the suffix
#: branch starts a character earlier, so it wins the match and yields `\vec{m} v` -- the arrow
#: on the mass rather than on the velocity, which is a statement about different physics.
RE_ACCENT_SUFFIX = re.compile(r'(\\?[A-Za-z]+)\s*\\vec(?![A-Za-z{])')


def accents(body: str) -> str:
    r"""`\vec B` and a stranded `B\vec` both -> `\vec{B}`."""
    body = RE_ACCENT_PREFIX.sub(lambda m: f'\\vec{{{m.group(1)}}}', body)
    return RE_ACCENT_SUFFIX.sub(lambda m: f'\\vec{{{m.group(1)}}}', body)


#: Relations TeX builds by **overstriking two glyphs**, and the pieces they arrive as.
#:
#: `\doteq` is a `.` set over an `=` and `\notin` a `/` over an `\in`; the PDF records two
#: placements at almost the same x, and the decode -- which reads along a baseline -- emits
#: both. So `04/p12` came out as `= \doteq 10`, two relations where the booklet printed one,
#: and `08/p23` as `V\notin/\langle …`, with the slash stranded after the symbol it belongs
#: on. Both orders are handled, because which piece is laid down first is the typesetter's
#: business and not stable.
#:
#: This is the whole list. It is not the general problem of overstriking -- that would need
#: the positions, which `assemble` has already spent -- but these two are what this corpus
#: actually contains, and naming them is better than leaving the doubled relation in the text.
COMPOSITES = (
    (r'=\s*\\doteq', r'\\doteq'),
    (r'\\doteq\s*=', r'\\doteq'),
    (r'\\notin\s*/', r'\\notin'),
    (r'/\s*\\notin', r'\\notin'),
)

RE_COMPOSITES = tuple((re.compile(a), b) for a, b in COMPOSITES)


def composites(body: str) -> str:
    r"""Put an overstruck relation back together: `= \doteq` -> `\doteq`."""
    for pattern, replacement in RE_COMPOSITES:
        body = pattern.sub(replacement, body)
    return body


#: What mupdf resolves some maths glyphs to, against what LaTeX needs. These arrive only from
#: a font named well enough for mupdf to read its glyph names -- `11.pdf` is the one booklet
#: like that -- so the encoding tables never see them and nothing else would fix them up.
UNICODE_MATHS = {
    '−': '-',          # MINUS SIGN, which TeX writes as a plain hyphen inside maths
    '◦': r'\circ',     # WHITE BULLET, which is how `cmsy`'s degree ring resolves
    '∘': r'\circ',
    '√': r'\sqrt',
    '·': r'\cdot',
    '≤': r'\leq', '≥': r'\geq', '≠': r'\neq',
    '≈': r'\approx', '≡': r'\equiv', '±': r'\pm',
    '→': r'\rightarrow', '⇒': r'\Rightarrow',
    '∞': r'\infty', '∂': r'\partial',
    # Greek, which a font with readable glyph names resolves to the letter itself.
    # XeLaTeX would set some of these from the text font and drop the rest with a
    # `Missing character` in the log and nothing on the page -- the failure mode
    # `core/latex/math.tex` warns about -- so they are spelled as macros throughout.
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
    'ε': r'\varepsilon', 'ζ': r'\zeta', 'η': r'\eta', 'θ': r'\theta',
    'ι': r'\iota', 'κ': r'\kappa', 'λ': r'\lambda', 'μ': r'\mu',
    'ν': r'\nu', 'ξ': r'\xi', 'π': r'\pi', 'ρ': r'\rho',
    'σ': r'\sigma', 'τ': r'\tau', 'υ': r'\upsilon', 'φ': r'\varphi',
    'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega', 'Γ': r'\Gamma',
    'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda', 'Ξ': r'\Xi',
    'Π': r'\Pi', 'Σ': r'\Sigma', 'Υ': r'\Upsilon', 'Φ': r'\Phi',
    'Ψ': r'\Psi', 'Ω': r'\Omega', 'ϕ': r'\phi', 'ϑ': r'\vartheta',
    'ϱ': r'\varrho',
}

RE_UNICODE_MATHS = re.compile('|'.join(map(re.escape, UNICODE_MATHS)))


def unicode_maths(body: str) -> str:
    """
    `−` -> `-`, `◦` -> `\\circ`, `κ` -> `\\kappa`: what a readable font gives, as TeX.

    A control word that runs into a letter is a *different* control word, so `κv` has to come
    out as `\\kappa v` and not `\\kappav`, which is undefined and stops the build.
    """
    def substitute(m: re.Match[str]) -> str:
        macro = UNICODE_MATHS[m.group(0)]
        tail = m.string[m.end():m.end() + 1]
        return macro + (' ' if macro[:1] == '\\' and tail.isalpha() else '')

    return RE_UNICODE_MATHS.sub(substitute, body)


#: A run that is nothing but punctuation, *and is attached to what precedes it*, is
#: punctuation, whatever font it was set in. These booklets write a decimal comma, a unit
#: solidus and the `.` between the parts of a compound unit in maths mode, so `11.pdf`
#: produced `4$,$2 kJ$.$kg` -- five dollar signs around three characters of ordinary prose.
RE_PUNCTUATION = re.compile(r'^[.,/;:!?\-]+$')


def is_punctuation(body: str, before: str) -> bool:
    """
    Is this whole maths run punctuation to be set as prose, given what it follows?

    **Attachment is what decides it, not the character.** A `/` butted against a letter is a
    solidus -- `km/h`, `kg.m`, `4,2` -- while a `/` standing alone with a space either side is
    a *symbol*: in the volumes whose subset fonts are scrambled, `cmmi`'s `/` is what an
    unreadable letter decodes to, and `04/p04` says "klesá nadol so zrýchlením $/$", denoting
    an acceleration by it. Unwrapping that one loses the reader the only signal that the
    character is standing in for a symbol. So the rule reaches only inside a word or a number.
    """
    return bool(RE_PUNCTUATION.match(body)) and before[-1:] not in ('', ' ')


def tidy(body: str) -> tuple[str, list[str]]:
    """Everything, in the order that matters: quantities, then differences, then spacing."""
    body, missing = quantities(unicode_maths(body))
    return spacing(accents(composites(operators(differences(body))))), missing


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

    **And it must be a unit this corpus is known to write**, which is what `units.py` records.
    That gate is not belt-and-braces: pint will happily read `hg` as a hectogram and `c` as the
    speed of light, so a fountain came out playing at two hectograms, and `08/p30`'s `v = 0.2c`
    -- which is perfectly good physics -- hoisted to a unit pint renders as `\speed_of_light`,
    which is not TeX and stopped the build. Neither is a unit these authors write in a
    statement, and `units.py` says so. A unit outside it is reported, which is that module's
    documented contract, and the prose keeps it as written.
    """
    candidate = _reciprocal(tail) or tail
    if not re.fullmatch(r'[A-Za-z]+(?:/[A-Za-z]+)?', candidate):
        return None
    if candidate not in UNITS:
        return None
    try:
        from core.builder.jinja import ureg
        ureg.Quantity(1, candidate)
    except Exception:
        return None
    return candidate
