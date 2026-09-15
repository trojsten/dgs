r"""
The rewrite table: old TeX in, DGS Markdown out.

Two kinds of rule, and the distinction is the whole design.

**Silent rules** have one right answer. `\mrm{x}` is `\text{x}`; `v~ktorom` is `v\ ktorom`;
`\varepsilon` is `\epsilon` because `mdcheck`'s `vep` rule says so. These are applied and not
mentioned.

**Reported rules** do not. Whether a display ends a sentence, whether `\tfrac{2}{3}` wants
`\frac` or `\TwoThirds`, which part of an evaluator's note is the answer — only the sentence
decides, and a converter that picked would be inventing. These leave the source as it stands and
add a `%# TODO(rule)` line, which is Jinja's own comment prefix: stripped before pandoc, invisible
in the PDF, and greppable. The conversion is not finished while one remains.

**Nothing from `mathab.sty` survives into the output.** Every one of its macros is expanded here
into either plain maths or a DGS macro; none is carried across and none is redefined on the DGS
side. That is deliberate — the new tree should not inherit a 2009 dialect.
"""
import re

from tools.ancient import units
from tools.ancient.lex import match_brace

#: One-letter Slovak prepositions and conjunctions. `vlna` tied these to the following word, and
#: the house convention writes that tie as `\ `. Capitals included: sentences start with them.
TIED = set('vszokaiuVSZOKAIU')

#: Everything `mdcheck` bans outright, with what it wants instead.
LINTED = [
    (re.compile(r'\\varepsilon(?![a-zA-Z])'), r'\\epsilon'),          # vep
    (re.compile(r'\\implies(?![a-zA-Z])'), r'\\Implies'),             # imp
    (re.compile(r'\\Rightarrow(?![a-zA-Z])'), r'\\Implies'),          # rar
    (re.compile(r'\\then(?![a-zA-Z])'), r'\\Implies'),                # mathab's spelling of the same
    (re.compile(r'\\SI(?![a-zA-Z])'), r'\\qty'),                      # osi
]

#: `mathab.sty` and `include.tex` shorthands with an unambiguous modern spelling. `\matheq`,
#: `\mathplus` and `\mathminus` are used in the archive and defined in no shipped `mathab.sty`:
#: the characters were made active and these were meant to be the saved originals.
SHORTHAND = [
    (re.compile(r'\\matheq(?![a-zA-Z])'), '='),
    (re.compile(r'\\mathplus(?![a-zA-Z])'), '+'),
    (re.compile(r'\\mathminus(?![a-zA-Z])'), '-'),
    (re.compile(r'\\(?:mrm|mathrm|text|textrm)\{(\d+)\}'), r'\1'),
    (re.compile(r'\\mrm(?![a-zA-Z])'), r'\\text'),
    (re.compile(r'\\textrm(?![a-zA-Z])'), r'\\text'),
    (re.compile(r'\\mathrm(?![a-zA-Z])'), r'\\text'),
    (re.compile(r'\\R(?![a-zA-Z])'), r'\\mathbb{R}'),
]


def ties(text: str) -> str:
    r"""`v~ktorom` -> `v\ ktorom`, leaving every other `~` for a human."""
    def sub(m):
        return f'{m.group(1)}\\ ' if m.group(1) in TIED else m.group(0)
    return re.sub(r'(?<![a-zA-ZáäčďéíĺľňóôŕšťúýžÁČĎÉÍĽŇÓŠŤÚÝŽ])([a-zA-Z])~', sub, text)


def trhaciealt(text: str) -> str:
    r"""
    `\trhaciealt{A}{B}` -> `A`. The tear-off sheet's version, and there is only one now.

    2009's `include.tex` defines it twice: `\def\trhaciealt#1#2{#2}` at the top, and `#1` again
    inside the trhačka, so the booklet printed the second version and the tear-off sheet the
    first. `OPT/polsosovka` is the only user, and its two are one drawing at 100 % and 80 % --
    `polsosovka_zad.svg` is 400.5 x 231, `polsosovka_zad_small.svg` 320.4 x 184.8, same two
    labels. So take the first: it is the master, and in the modern layout the size is a
    `height=` on the Markdown rather than a second export.
    """
    while True:
        m = re.search(r'\\trhaciealt(?![a-zA-Z])\s*(?=\{)', text)
        if not m:
            return text
        first = match_brace(text, m.end())
        second = match_brace(text, first)
        text = text[:m.start()] + text[m.end() + 1:first - 1] + text[second:]


def _enclosing_group(text: str, pos: int) -> tuple[int, int] | None:
    r"""
    The innermost brace group containing `pos`, as (start, end past the `}`), or None.

    A backward `rfind('{')` will not do, and this is not a hypothetical: the numerator of
    `{\bigl(\lambda d + \tfrac{1}{2}M\bigr)g \over \sin\alpha}` ends in a *closed* group, so the
    nearest `{` behind the `\over` is `\tfrac`'s `{2`, whose own `}` comes before the `\over`.
    Slicing on it yields an empty denominator and leaves the `\over` in place -- which spun
    forever. So scan forward, keeping the open groups on a stack; the top of it is the answer.
    """
    stack, i = [], 0
    while i < pos:
        c = text[i]
        if c == '\\':
            i += 2
            continue
        if c == '{':
            stack.append(i)
        elif c == '}' and stack:
            stack.pop()
        i += 1
    if not stack:
        return None
    return stack[-1], match_brace(text, stack[-1])


def _unwrap(body: str) -> str:
    r"""
    `{v+c}` -> `v+c`, where the braces only held the operand together for `\over`.

    `\frac` takes its arguments in braces of its own, so a group that wraps the *whole* operand
    is now doing nothing. One that wraps only part of it -- `{a}b` -- is left alone.
    """
    if body.startswith('{'):
        try:
            if match_brace(body, 0) == len(body):
                return body[1:-1].strip()
        except ValueError:
            pass
    return body


def over_to_frac(text: str) -> tuple[str, list[str]]:
    r"""
    plain TeX `{a \over b}` -> `\frac{a}{b}`, which is what pandoc can read.

    A `\over` with no group around it -- legal plain TeX, `$a \over b$` -- is left alone and
    reported: its numerator is everything back to the opening `$`, which is a judgement about
    where the formula starts rather than a brace to match. 2009 has none.
    """
    notes, skip = [], 0
    while True:
        found = list(re.finditer(r'\\over(?![a-zA-Z])', text))
        if skip >= len(found):
            return text, notes
        m = found[skip]
        group = _enclosing_group(text, m.start())
        if group is None:
            notes.append(r'over: a bare `\over` with no brace group around it, left as written')
            skip += 1
            continue
        start, end = group
        num = _unwrap(text[start + 1:m.start()].strip())
        den = _unwrap(text[m.end():end - 1].strip())
        text = f'{text[:start]}\\frac{{{num}}}{{{den}}}{text[end:]}'


#: A unit, in either spelling the archive uses: `\unit{km/h}` with a literal body, or one of the
#: zero-argument macros standing for a whole unit. Both reach `units.lookup`, which knows both.
RE_UNIT = re.compile(r'\\unit(?![a-zA-Z])\s*(?=\{)|\\(?:' +
                     '|'.join(n[1:] for n in units.MACRO_UNITS) + r')(?![a-zA-Z])')
#: A literal magnitude sitting immediately before a unit, digit groups and all. The `\,` groups
#: have to be part of the match, not left behind it: `0.133\,33\unit{rad}` otherwise matched only
#: the final `33` and came out `0.133\,\qty{33}{\radian}` -- a corruption, and a silent one, since
#: a magnitude *was* found and so nothing was reported.
RE_MAGNITUDE = re.compile(r'(-?\d+(?:[.,]\d+)?(?:\\,\d+)*)\s*$')


def quantities(text: str) -> tuple[str, list[str]]:
    r"""
    `$120\unit{km/h}$` -> `$\qty{120}{\kilo\metre\per\hour}$`, and `$30\unit{\sdeg}$` -> `\ang{30}`.

    Both of the archive's spellings are handled in one pass, and they have to be: `\kmh` expands
    to `\mrm{km\,h^{-1}}`, so 2009 writes it *inside* the old `\unit{}` -- `$72\unit{\kmh}$` --
    and expanding the macro first would build `\unit{\unit{\kilo\metre\per\hour}}`. Two `\Ce` are
    bare, with no `\unit{}` around them, so both forms are real.

    Only where the magnitude is a plain literal immediately before. A magnitude that is an
    expression -- `$\tfrac{160}{9}\unit{km\,h^{-2}}$` -- cannot become a `\qty`, which refuses
    anything but a number, so those are reported instead.
    """
    notes, out, i = [], [], 0
    for m in RE_UNIT.finditer(text):
        if m.start() < i:
            continue                                    # inside a `\unit{}` already consumed
        if m.group(0).startswith('\\unit'):
            try:
                end = match_brace(text, m.end())
            except ValueError:
                continue
            body = text[m.end() + 1:end - 1]
        else:
            end, body = m.end(), m.group(0)
        siunitx = units.lookup(body)
        if siunitx is None:
            notes.append(f'unit: `\\unit{{{body}}}` is not in the table, left as written')
            continue
        before = text[i:m.start()]
        num = RE_MAGNITUDE.search(before)
        out.append(text[i:i + num.start(1)] if num else before)
        if num and '\\,' in num.group(1):
            # siunitx groups digits itself, from `\qty`'s own settings, so the archive's manual
            # `\,` between groups has to come out of the number.
            notes.append(f'unit: `{num.group(1)}` had its digit groups spelled with `\\,`; '
                         f'siunitx groups them itself, so the number is now '
                         f'`{num.group(1).replace(chr(92) + ",", "")}`')
        magnitude = num.group(1).replace('\\,', '') if num else ''
        if num and siunitx == r'\degree':
            # An angle is `\ang{45}` here, not `\qty{45}{\degree}` -- 176 files say so.
            out.append(f'\\ang{{{magnitude}}}')
        elif num:
            out.append(f'\\qty{{{magnitude}}}{{{siunitx}}}')
        else:
            out.append(f'\\unit{{{siunitx}}}')
            notes.append(f'unit: `\\unit{{{body}}}` had no literal magnitude before it; '
                         f'wrote `\\unit{{}}`, check whether a `\\qty{{}}{{}}` is meant')
        i = end
    out.append(text[i:])
    return ''.join(out), notes


#: What solutions here call their displays. `solution-unlabelled` wants every block in a solution
#: labelled -- the label is what makes pandoc number the equation -- and the repository's own
#: habit is ordinals: `third` 29 times, `fourth` 27, `second` 21, `first` 18.
ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth',
            'ninth', 'tenth', 'eleventh', 'twelfth']


def displays(text: str, label_prefix: str | None = None) -> tuple[str, list[str]]:
    r"""
    `$$…$$` -> the block form, body indented four spaces.

    With `label_prefix` (a problem id) every block gets `{#eq:<id>:<ordinal>}`, which is what
    `solution-unlabelled` asks of a solution. Statements mostly go unlabelled, so problem bodies
    are converted without one.

    The terminal `\,\.` or `\,,` is kept as plain punctuation and reported: whether a display ends
    the sentence decides whether a blank line follows it, and only the sentence knows.
    """
    notes = []
    counter = iter(ORDINALS)

    def sub(m):
        body = m.group(1).strip()
        punct = ''
        tail = re.search(r'(\\,)?\s*(\\\.|\\,|[.,;])\s*$', body)
        if tail:
            punct = tail.group(2).replace('\\.', '.').replace('\\,', ',')
            body = body[:tail.start()].rstrip()
            notes.append(f'display: ended with `{tail.group(0).strip()}`, kept as `{punct}` -- '
                         f'check the blank line after it agrees (see `display-paragraph`)')
        lines = [('    ' + l.strip()) if l.strip() else '' for l in body.split('\n')]
        label = ''
        if label_prefix:
            try:
                label = f' {{#eq:{label_prefix}:{next(counter)}}}'
            except StopIteration:
                notes.append('display: more than twelve blocks -- name the rest by hand')
        return '$$\n' + '\n'.join(lines) + punct + '\n$$' + label

    return re.sub(r'\$\$(.*?)\$\$', sub, text, flags=re.S), notes


#: Binary operators `mdcheck` insists on having spaces around (`EqualsSpaces`, `PlusSpaces`,
#: `CdotSpaces`). The archive writes `mh+MH` and `={H(2m+3M)\over…}` freely.
#: A display, or an inline formula. Inline maths may run over a line break -- 15 of 2009's do --
#: but never over a blank line, which would mean an unmatched `$` had swallowed a paragraph.
RE_MATH = re.compile(r'\$\$.*?\$\$|\$(?:[^$\n]|\n(?!\n))*\$', re.S)
RE_RELATION = re.compile(r'\s*(\\approx|\\doteq|\\geq|\\leq|\\gg|\\ll|=)\s*')
#: A `+` with something either side of it, and not the unary one that opens a group or follows
#: another operator, nor one inside a superscript like `10^{+3}`.
RE_PLUS = re.compile(r'(?<=[\w}\)\]])\s*\+\s*(?=[\w\\{\(])')
RE_CDOT = re.compile(r'\s*\\cdot\s*')


def operator_spaces(text: str) -> str:
    r"""`mh+MH` -> `mh + MH`, inside maths only."""
    def space(m):
        body = m.group(0)
        # `\qty{2.5}{\kilo\gram}` and label braces must not be touched: a space inside a siunitx
        # argument is a different thing entirely.
        guarded = re.split(r'(\\(?:qty|num|qtylist|ang)\{[^}]*\}(?:\{[^}]*\})?)', body)
        for i in range(0, len(guarded), 2):
            piece = RE_RELATION.sub(lambda r: f' {r.group(1)} ', guarded[i])
            piece = RE_PLUS.sub(' + ', piece)
            piece = RE_CDOT.sub(r' \\cdot ', piece)
            guarded[i] = piece
        return ''.join(guarded)
    return RE_MATH.sub(space, text)


def markup(text: str) -> str:
    """TeX font styling -> Markdown, which is what `mdcheck`'s `txp` rule demands."""
    for macro, wrap in (('textbf', '**'), ('textit', '_'), ('emph', '_')):
        while True:
            m = re.search(r'\\' + macro + r'(?![a-zA-Z])\s*(?=\{)', text)
            if not m:
                break
            end = match_brace(text, m.end())
            text = text[:m.start()] + wrap + text[m.end() + 1:end - 1] + wrap + text[end:]
    return text


def report_only(text: str) -> list[str]:
    r"""Everything that needs a person. Nothing here is rewritten."""
    notes = []
    for m in re.finditer(r'\\tfrac(?![a-zA-Z])', text):
        notes.append('tfrac: `\\tfrac` -- pick from the four fraction tiers '
                     '(vulgar glyph, `\\dfrac`, `\\nicefrac`, `\\frac`)')
    for m in re.finditer(r'(?<![a-zA-Z])([a-zA-Z]?)~', text):
        if m.group(1) not in TIED:
            notes.append(f'tie: `{text[max(0, m.start() - 12):m.end() + 12]!r}` -- a `~` that is '
                         f'not a one-letter preposition')
    for name in ('footnote', 'hskip', 'vskip', 'break', 'par', 'texttt', 'uv'):
        for _ in re.finditer(r'\\' + name + r'(?![a-zA-Z])', text):
            notes.append(f'macro: `\\{name}` has no Markdown equivalent here')
    # A `.` between digits needs no thought: `mathab.sty` printed it as a decimal comma, and so
    # does the modern pipeline (`core/i18n/sk.yaml`'s `output_decimal_marker`), so it transcribes
    # as itself. A `.` in maths that is *not* between digits would need a ruling -- 2009 has none,
    # but later years may.
    for m in re.finditer(r'\$[^$\n]*\$', text):
        for d in re.finditer(r'(?<![0-9\\])\.(?![0-9])', m.group(0)):
            notes.append(f'dot: a `.` in maths that is not a decimal point, in `{m.group(0)[:40]}`')
    return notes
