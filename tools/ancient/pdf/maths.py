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
from pathlib import Path

import yaml

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


#: Units `units.py` knows, whose bare form means something else in *these* booklets.
#:
#: `ms` is a millisecond to `units.py`, and that entry was written for 2014, which meant it.
#: 1999-2008 write a metre per second as `ms^{-1}` and set the exponent on a row of its own, so
#: wherever the decode failed to reattach it a speed became a duration: `08/p25`'s boat came
#: out at `\qty{0.954}{\milli\second}`, and the reader has no way to tell. The reciprocal form
#: still converts -- `_reciprocal` splits it to `m/s` -- and only the bare one is refused, so
#: it lands in `report.md` as an unknown unit and stays in the prose as written.
AMBIGUOUS = {'ms'}


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
        unit = tail if tail in UNITS and tail not in AMBIGUOUS else _reciprocal(tail)
        if unit is not None:
            # siunitx parses the number itself and rejects a decimal comma outright -- `Invalid
            # number '88,10'` stopped volume 08's booklet. The comma is the Slovak separator and
            # is how the booklet prints it; siunitx puts it back on the page from the locale,
            # so what goes in the source is a point, as it is everywhere else in the repository.
            return f'\\qty{{{number.replace(",", ".")}}}{{{UNITS[unit]}}}'
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
    # Unicode has more than one code point for several of these, and a font with readable
    # glyph names hands back whichever the face declares. `\Delta` resolves to U+2206
    # INCREMENT rather than the Greek capital, and `\Omega` to U+2126 OHM SIGN rather than
    # U+03A9 -- both of which MinionPro has no glyph for, so XeLaTeX logged `Missing
    # character` and set *nothing*: 59 deltas and 3 ohms straight off the page, with the
    # build green. That is the failure `core/latex/math.tex` warns about, found by reading
    # the log rather than the PDF.
    '∆': r'\Delta', 'Ω': r'\Omega',
    '′': r'\prime', '″': r'\prime\prime',
    '⟨': r'\langle', '⟩': r'\rangle',
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


#: A degree sign on a number, in the two shapes the decode produces. `convertor.py` refuses
#: `^\circ` outright -- `RegexFailure(r'\^\\circ|\^{\\circ}')` -- because the house spelling
#: is siunitx's `\ang{}`, and it is a build error rather than a warning. 143 of these across 62
#: files, which is what stopped `11`'s booklet the first time it had a target to build at all.
#:
#: Two shapes because the ring is set in `cmsy` while the number is not: usually they share a
#: maths run and give `30^{\circ}`, but where the number came from the prose face the run
#: closes between them and the line reads `30$^{\circ}$`.
RE_DEGREES_SPLIT = re.compile(r'(\d+)\$\^\{\\circ\}\$')
RE_DEGREES = re.compile(r'(\d+)\s*\^\{?\\circ\}?')


def degrees(text: str) -> str:
    r"""`30^{\circ}` and `30$^{\circ}$` both -> `\ang{30}`."""
    text = RE_DEGREES_SPLIT.sub(r'$\\ang{\1}$', text)
    return RE_DEGREES.sub(r'\\ang{\1}', text)


#: A radical whose radicand the decode could not find. `\sqrt` is one glyph -- the sign -- and
#: its vinculum is a *rule*, with the content under it on rows of its own, so a radical split
#: across a display arrives as a bare `\sqrt` and stops the build with `Missing { inserted`.
#:
#: Given `{}` it compiles, and it prints an empty radical sign: visibly, unmissably incomplete
#: on the page, which is what this ought to look like until someone rebuilds it from the
#: original. Not `\sqrt{x}` guessed from a neighbouring row, and not dropped either.
RE_BARE_RADICAL = re.compile(r'\\sqrt(?![A-Za-z0-9{])')


#: `\vec` is in the same position: the arrow is a glyph of its own and the symbol under it may
#: be on another row, so `02/p26` decoded to a line that is one bare `\vec`.
RE_BARE_ACCENT = re.compile(r'\\vec(?![A-Za-z{])')


def radicals(body: str) -> str:
    r"""
    `\sqrt` and `\vec` with nothing to act on -> `\sqrt{}`, `\vec{}`.

    Both compile that way and both then *show* themselves -- an empty radical sign, an arrow
    over nothing -- which is what an unreconstructed one should look like until someone
    rebuilds it from the page. Left bare they are `! Missing { inserted.` and no booklet at all.
    """
    return RE_BARE_ACCENT.sub(r'\\vec{}', RE_BARE_RADICAL.sub(r'\\sqrt{}', body))


#: Every control word the decode can emit: the encoding tables' own values, plus the ones this
#: module introduces. Collected rather than listed, so it cannot drift from the tables.
def _known_macros() -> frozenset[str]:
    from tools.ancient.pdf import encodings, glyphs
    tables = [encodings.MATH_ITALIC, encodings.MATH_SYMBOL, encodings.OT1, encodings.T1]
    # The hand-read tables are the other half, and leaving them out is not harmless: they are
    # where every AMS symbol lives, so `\leqslant` met a `separate_macros` that knew `\leq` and
    # not the whole word, and 22 relations across `03` came out as the longest known prefix
    # plus a word of prose -- `$\mu_1 \leq slant F\cos\alpha$`, which compiles.
    tables += [t for path in sorted((Path(glyphs.__file__).parent / 'glyphs').glob('*.yaml'))
               for t in (yaml.safe_load(path.read_text()) or {}).values()
               if isinstance(t, dict)]
    names = {v[1:] for table in tables for v in table.values()
             if isinstance(v, str) and v.startswith('\\') and v[1:].isalpha()}
    names |= {m[1:] for m in UNICODE_MATHS.values() if m.startswith('\\')}
    names |= set(OPERATORS) | {'qty', 'frac', 'sqrt', 'vec', 'ang', 'FDiff', 'Diff',
                               'PDiff', 'UDiff', 'text', 'mathrm', 'circ'}
    return frozenset(names)


KNOWN_MACROS = _known_macros()

RE_CONTROL_WORD = re.compile(r'\\([A-Za-z]+)')


def separate_macros(body: str) -> str:
    r"""
    Keep a control word off the letters after it: `\betao` -> `\beta o`.

    TeX reads a control word as the **longest run of letters** after the backslash, so a Greek
    letter followed by a variable is one undefined macro rather than two symbols -- `\deltax`,
    `\pil`, `\upsilonj`, `\niY`. The decode produces these constantly, because the glyph stream
    has no spaces in it and a `cmmi` delta butted against a `cmmi` x is exactly what a
    derivative looks like.

    The split is made only where the prefix is a macro **this decoder emits**, longest first;
    anything else is left exactly as it stands rather than cut at a guess.
    """
    def split(m: re.Match[str]) -> str:
        word = m.group(1)
        if word in KNOWN_MACROS:
            return m.group(0)
        for cut in range(len(word) - 1, 0, -1):
            if word[:cut] in KNOWN_MACROS:
                return f'\\{word[:cut]} {word[cut:]}'
        return m.group(0)

    return RE_CONTROL_WORD.sub(split, body)


def scripts_once(body: str) -> str:
    r"""
    Give a base at most one superscript and one subscript, by re-basing the repeats.

    A booklet's display maths puts each script on a row of its own and several can end up
    attached to the same symbol, which is how `07/p01` produced
    `^{\frac{140km}{6kmh}6}_{-1}^{13}` -- two superscripts on one base, and `! Double
    superscript.` TeX's own idiom for that is an empty group, so `^{A}_{B}{}^{C}` says exactly
    what the rows say and compiles. Nothing is dropped and nothing is merged: merging would
    invent a single exponent out of two that the page shows separately.
    """
    out: list[str] = []
    used: set[str] = set()
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c not in '^_':
            if not c.isspace():
                used = set()            # a new base atom
            out.append(c)
            i += 1
            continue
        if c in used:
            out.append('{}')
            used = set()
        used.add(c)
        out.append(c)
        i += 1
        if i >= n:
            break
        if body[i] == '{':              # a braced argument, nesting and all
            depth, start = 0, i
            while i < n:
                if body[i] == '{':
                    depth += 1
                elif body[i] == '}':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            out.append(body[start:i])
        elif body[i] == '\\':           # a control word
            start = i
            i += 1
            while i < n and body[i].isalpha():
                i += 1
            out.append(body[start:i])
        else:                           # a single character
            out.append(body[i])
            i += 1
    return ''.join(out)


#: A combining mark or spacing modifier that reached a formula. `_apply` places an accent on
#: its base letter and **leaves it off rather than guess** when the pair is not one Slovak has,
#: so the odd one falls through -- and inside maths it does more than look wrong. XeTeX gives
#: some Unicode letters catcode 11, so `09/p26`'s stray caron was read as part of the control
#: word in front of it and the whole booklet stopped on an undefined `\wpˇ`.
#:
#: Two of them in the ten booklets, and a caron carries nothing in a formula anyway.
RE_STRAY_MARK = re.compile(r'[\u0300-\u036f\u02b0-\u02ff]')


def strip_marks(body: str) -> str:
    """Drop an accent that reached a formula, which is an accent with no letter to sit on."""
    return RE_STRAY_MARK.sub('', body)


#: TeX characters the decode can emit literally, which mean something else inside maths.
#:
#: Pandoc escapes these in prose, and passes a `$...$` body through untouched -- so a percent
#: sign decoded out of `cmr` reaches the TeX raw, and **starts a comment**. `02/p34` asks about
#: a 50 % alcohol and printed `Majme 50 alkohol`: the sign gone, the closing `\)` pushed to the
#: next line, no warning anywhere. `&` and `#` are the same class and fail loudly instead.
RE_SPECIALS = re.compile(r'(?<!\\)([%&#])')


def specials(body: str) -> str:
    r"""`50%` -> `50\%`, inside maths where pandoc will not do it for you."""
    return RE_SPECIALS.sub(r'\\\1', body)


#: A percentage. `50%` is a quantity like any other and the repository writes it
#: `\qty{50}{\percent}` -- 213 of them -- so the decode spells it that way too rather than
#: leaving a bare sign for `specials` to escape.
#:
#: Two shapes again, for the reason `RE_DEGREES` has two: the sign is set in `cmr` and the
#: number may or may not share its run, so the line reads `$50%$` or `50%` with the number in
#: the prose face.
RE_PERCENT = re.compile(r'(?<![\w\\])(\d+(?:[.,]\d+)?)\s*\\?%')


def percents(body: str) -> str:
    r"""`50%` -> `\qty{50}{\percent}`, with the decimal comma normalised as siunitx wants."""
    return RE_PERCENT.sub(lambda m: f'\\qty{{{m.group(1).replace(",", ".")}}}{{\\percent}}', body)


#: A `$...$` span, so a line-level rule can leave the maths alone and work on the prose.
RE_MATHS_SPAN = re.compile(r'\$[^$\n]*\$')


def in_prose(text: str, rule) -> str:
    """Apply a rule to the prose of a line, leaving every `$...$` span untouched."""
    parts = RE_MATHS_SPAN.split(text)
    spans = RE_MATHS_SPAN.findall(text)
    out = [rule(parts[0])]
    for span, part in zip(spans, parts[1:]):
        out.append(span)
        out.append(rule(part))
    return ''.join(out)


def prose_percents(text: str) -> str:
    r"""A percentage the decode left in the prose: `o 10% menšie` -> `o $\qty{10}{\percent}$`."""
    return in_prose(text, lambda s: RE_PERCENT.sub(
        lambda m: f'$\\qty{{{m.group(1).replace(",", ".")}}}{{\\percent}}$', s))


#: A run of letters, with the full stop an abbreviation ends on.
RE_WORD = re.compile(r'[^\W\d_]+\.?')

#: `\text{\text{x}}`, which `prose_words` makes if it meets a word already wrapped.
RE_DOUBLE_TEXT = re.compile(r'\\text\{\\text\{([^{}]*)\}\}')


def prose_words(body: str) -> str:
    r"""
    A word with an accent in it is prose, and prose in maths goes in `\text{}`.

    The maths fonts can set `konst.` and cannot set `konšt.`: MinionPro's maths cuts carry no
    accented letters, so a bare one is a `Missing character` in the log and **nothing at all on
    the page** -- the same silent loss a `\TwoFifths` would be. `06/earth-falls` writes
    `$T^2/a^3 = konšt.$` and lost its š six times over while the build stayed green.

    Only a run that actually holds one is touched, so `\alpha`, `mgh` and every ASCII variable
    are left exactly as they were. That is deliberately narrower than "a word in maths belongs
    in `\text{}`", which is true but is a judgement about each site; this is the subset where
    the alternative is ink that does not arrive.
    """
    wrapped = RE_WORD.sub(
        lambda m: f'\\text{{{m.group(0)}}}' if any(ord(c) > 127 for c in m.group(0))
        else m.group(0), body)
    return RE_DOUBLE_TEXT.sub(r'\\text{\1}', wrapped)


def tidy(body: str) -> tuple[str, list[str]]:
    """Everything, in the order that matters: quantities, then differences, then spacing."""
    body, missing = quantities(percents(unicode_maths(strip_marks(body))))
    body = radicals(accents(composites(operators(differences(body)))))
    body = prose_words(specials(separate_macros(body)))
    return spacing(scripts_once(body)), missing


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
