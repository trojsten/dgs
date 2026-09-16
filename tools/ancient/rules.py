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
#: Prepositions of more than one letter that take the same non-breaking space. 2009 to 2012 tie
#: almost nothing but the one-letter ones, so these went unnoticed until 2013, which has 43 --
#: and they were neither rewritten nor reported, because the reporter's own lookbehind made a
#: `zo~` invisible to it. A `~` after any other word is still a person's to decide.
TIED_WORDS = {'vo', 'zo', 'so', 'ku', 'po', 'od', 'na', 'do', 'za', 'bez',
              'pre', 'pri', 'nad', 'pod', 'cez'}
#: Slovak, so the word before a `~` may be accented.
LETTER = 'a-zA-ZáäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ'


def _tied(word: str) -> bool:
    """Is this the kind of word a `~` binds to what follows -- a short preposition?"""
    return word in TIED if len(word) == 1 else word.lower() in TIED_WORDS

#: Everything `mdcheck` bans outright, with what it wants instead.
LINTED = [
    (re.compile(r'\\varepsilon(?![a-zA-Z])'), r'\\epsilon'),          # vep
    (re.compile(r'\\implies(?![a-zA-Z])'), r'\\Implies'),             # imp
    (re.compile(r'\\Rightarrow(?![a-zA-Z])'), r'\\Implies'),          # rar
    (re.compile(r'\\then(?![a-zA-Z])'), r'\\Implies'),                # mathab's spelling of the same
    (re.compile(r'\\SI(?![a-zA-Z])'), r'\\qty'),                      # osi
    # Nothing sits between a delimiter and what it delimits: `\left( x \right)` and
    # `\dfrac{ ab + ac}{ bc }` are how 2013 writes almost every bracket, and `mdcheck` has a
    # rule per side of each. Newlines are left alone -- a display body is indented on its own
    # line and this runs before `displays` puts one there.
    (re.compile(r'\\left([([])[ \t]+'), r'\\left\1'),                  # slp
    (re.compile(r'[ \t]+\\right([)\]])'), r'\\right\1'),              # srp
    (re.compile(r'\{[ \t]+(?=\S)'), '{'),                             # lbw
    (re.compile(r'(?<=\S)[ \t]+\}'), '}'),                            # rbw
    # `\frac 1 2` -- single-token arguments with the braces left off, which `mdcheck` reads as
    # a `\frac` with no numerator at all.
    (re.compile(r'\\([dt]?frac)[ \t]+(\w)[ \t]+(\w)'), r'\\\1{\2}{\3}'),
    (re.compile(r'([Mm])ôžme(?![a-záäčďéíĺľňóôŕšťúýž])'), r'\1ôžeme'),   # mzm
    (re.compile(r'\bt\.j\.'), 't. j.'),                                # tjj
    # An angle written by hand rather than through `\unit{}`: `$\alpha = 45^{\circ}$`, and
    # `\sin\left(90^{\circ} - \alpha\right)`. Not a temperature -- a `C` after the sign means
    # `upright_units` has already folded it into the box and the table will make it `\celsius`.
    (re.compile(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(?:\^\{\\circ\}|\^\\circ(?![a-zA-Z]))'
                r'(?!\s*\\?(?:text|mathrm)?\{?C)'), r'\\ang{\1}'),
]


def lone_dollars(text: str) -> str:
    r"""
    A line that is nothing but `$` is a display delimiter the author spelled short.

    From 2013 on the archive writes a display as a single `$` on its own line, the body, and
    another `$` -- 27 in 2013, 15 in 2014, 48 in 2015, and none before. TeX takes that as
    *inline* maths with the newlines as spaces, which is what the 2013 booklet printed: page 19
    sets $\Delta t = t/N$ in the middle of the paragraph and runs straight on into the next
    sentence with no break. The `$$` two lines further down the same file is the author saying
    what was meant. Runs before `displays`, which then sees an ordinary block.
    """
    return RE_LONE_DISPLAY.sub(
        lambda m: f"$$\n{m['body'].rstrip()}{m['punct']}\n$$", text)


#: The pair, matched as one: an opening line that is nothing but `$`, a body, and a closing line
#: that is `$` and at most a full stop, comma or semicolon. As a pair, because `KVAP/divnavoda`
#: closes with `$.` -- converting the two lines independently would have turned the opener into
#: `$$` and left the closer alone, and every paragraph after it was swallowed into the display.
RE_LONE_DISPLAY = re.compile(r'(?m)^[ \t]*\$[ \t]*\n(?P<body>.*?)\n[ \t]*\$(?P<punct>[.,;]?)[ \t]*$',
                             re.S)

def inline_math(text: str) -> str:
    r"""
    `$ x $` -> `$x$`. Pandoc will not read either delimiter with a space beside it.

    Its rule is that an opening `$` is followed by a non-space and a closing one preceded by
    one, so `ako $ \dfrac{a}{b} = c$` is not maths at all: the dollars stay literal, the
    backslashes reach TeX as text, and the build stops at `Missing $ inserted`. 2013 writes 17
    of these and the years before it none. Runs after `displays`, so a `$$` block is already
    on its own lines and every `$` left on a line of prose opens or closes inline maths.
    """
    out, display = [], False
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('$$') or stripped.startswith('}$$'):
            display = not display
        if display or line.startswith('%#') or '$' not in line:
            out.append(line)
            continue
        # Split on the delimiters: with an even number of them the odd pieces are the maths,
        # and each is stripped at both ends. Prose keeps its spaces, including the one after a
        # closing `$`.
        pieces = line.split('$')
        if len(pieces) % 2 == 0:                      # odd number of `$`, so none of them pair
            out.append(line)
            continue
        out.append('$'.join(p.strip() if i % 2 else p for i, p in enumerate(pieces)))
        continue
    return '\n'.join(out)

def line_breaks(text: str) -> str:
    r"""
    A prose line ending in `\\` is a paragraph break, and is written as one.

    The archive uses `\\` both ways: as the row separator inside a display, where it means
    what it says, and at the end of a paragraph of prose, where TeX's forced break is how the
    author asked for the next sentence to start on its own line. Markdown's forced break is a
    blank line, and a trailing `\\` left in prose sets a literal one. Runs after `displays`,
    so a display's rows are recognisable by their delimiters and left alone.
    """
    out, display = [], False
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('$$') or stripped.startswith('}$$'):
            display = not display
        if not display and stripped.endswith('\\\\'):
            out.extend([line.rstrip()[:-2].rstrip(), ''])
            continue
        out.append(line)
    return '\n'.join(out)

#: `mathab.sty` and `include.tex` shorthands with an unambiguous modern spelling. `\matheq`,
#: `\mathplus`, `\mathminus`, `\mathdiv` and `\mathless` are used in the archive and defined
#: in no shipped `mathab.sty`: the characters were made active and these were meant to be the
#: saved originals. There are 23 across the seven years, and every one is the plain character.
SHORTHAND = [
    # `.` was made active in maths to print the decimal comma, so `\.` was how the archive
    # wrote a *literal* full stop -- in `\mrm{priem\.}`, and at the end of a display. Today the
    # decimal comma is siunitx's `output_decimal_marker` and a `.` is a `.`; `mdcheck`'s `tgc`
    # rule bans `\.` outright.
    (re.compile(r'\\\.'), '.'),
    # csplain's compound hyphen, which the archive writes between a symbol and a Slovak ending:
    # `$y$\=ová`, `$k$\=krát`. It is a hyphen that also permits hyphenation on both sides, and
    # Markdown has no spelling for the second half -- nor any need of one here, since these are
    # all short.
    (re.compile(r'\\='), '-'),
    # And the thin space the archive put before that stop. There is not one `\,.` or `\,,` left
    # in phys: the house form sets the punctuation straight after the expression. A `\,` between
    # *digits* is a group separator and is left to `quantities`, which has already run.
    (re.compile(r'\\[,:; ](?=\\?[.,;])'), ''),
    # `\tg`, `\arctg` and `\cotg` are the Slovak and Czech names for the same three functions
    # LaTeX spells `\tan`, `\arctan` and `\cot`. `mathab.sty` defines them as operators; the
    # modern tree has no such macro and would set them as three italic letters.
    (re.compile(r'\\arctg(?![a-zA-Z])'), r'\\arctan'),
    (re.compile(r'\\cotg(?![a-zA-Z])'), r'\\cot'),
    (re.compile(r'\\tg(?![a-zA-Z])'), r'\\tan'),
    (re.compile(r'\\matheq(?![a-zA-Z])'), '='),
    (re.compile(r'\\mathplus(?![a-zA-Z])'), '+'),
    (re.compile(r'\\mathminus(?![a-zA-Z])'), '-'),
    (re.compile(r'\\mathdiv(?![a-zA-Z])'), '/'),
    (re.compile(r'\\mathless(?![a-zA-Z])'), '<'),
    (re.compile(r'\\mathgreater(?![a-zA-Z])'), '>'),
    (re.compile(r'\\(?:mrm|mathrm|text|textrm)\{(\d+)\}'), r'\1'),
    (re.compile(r'\\mrm(?![a-zA-Z])'), r'\\text'),
    (re.compile(r'\\textrm(?![a-zA-Z])'), r'\\text'),
    (re.compile(r'\\mathrm(?![a-zA-Z])'), r'\\text'),
    # 2013 sets a word subscript in typewriter -- `m_{\tt{ľad}}`. `cmtt8` has no Slovak letters,
    # so the `ľ` and the `á` dropped out of the page in silence (xelatex only writes
    # `Missing character:` to the log) and the subscript printed as `ad` and `npoj`.
    (re.compile(r'\\tt(?![a-zA-Z])'), r'\\text'),
    (re.compile(r'\\R(?![a-zA-Z])'), r'\\mathbb{R}'),
    # `\par` ends a paragraph, and Markdown's way of saying that is a blank line. 2014 writes
    # 39 of them on a line of their own and one at the end of a sentence; both mean the same
    # thing. A `\par` in the middle of a line would not, and is still reported.
    (re.compile(r'(?m)[ \t]*\\par(?![a-zA-Z])[ \t]*%?[ \t]*$'), '\n'),
]


def ties(text: str) -> str:
    r"""`v~ktorom` -> `v\ ktorom`, leaving every other `~` for a human."""
    def sub(m):
        return f'{m.group(1)}\\ ' if _tied(m.group(1)) else m.group(0)
    return re.sub(f'(?<![{LETTER}])([{LETTER}]{{1,3}})~', sub, text)


#: `5{,}97` -- the archive's way of writing a decimal comma that stays a decimal *marker*
#: rather than becoming punctuation with a space after it.
RE_DECIMAL_BRACES = re.compile(r'(?<=\d)\{,\}(?=\d)')


def decimal_braces(text: str) -> str:
    r"""
    `5{,}97` -> `5.97`, before anything looks for a magnitude.

    Today the comma is siunitx's `output_decimal_marker` and the *input* marker is `.`, so the
    braces come off and the comma with them. It has to happen first: `quantities` reading
    `5{,}97\times 10^{24}\unit{kg}` would find `97` as the magnitude, since a `}` is neither a
    digit nor a dot, and write `\qty{97e24}{\kilo\gram}` -- out by a factor of sixteen million.
    """
    return RE_DECIMAL_BRACES.sub('.', text)


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
#: The archive's *other* way of writing a unit, 66 times across five years: a thin space, an
#: upright box, and sometimes an exponent hung outside it -- `$360\,\textrm{m}$`,
#: `$120\,\textrm{km.h}^{-1}$`, `$2\,\mathrm{cm}$`. It is a unit in every way except that
#: `mathab.sty`'s `\unit` was not asked to set it.
RE_UPRIGHT_UNIT = re.compile(
    r'\\,\s*(?P<degree>\^\{?\\circ\}?\s*)?\\(?:textrm|mathrm|mrm|text)\{(?P<body>[^{}]*)\}(?:\^\{?(?P<exponent>-?\d+)\}?)?')


def upright_units(text: str) -> str:
    r'''
    `$360\,\textrm{m}$` -> `$360\unit{m}$`, so that `quantities` can see it.

    Only when the body is a unit the table knows. `\,\textrm{litrov kyslíka}` is a Slovak
    noun phrase and stays exactly where it is; so would anything else with no entry. An
    exponent written *outside* the box is folded back in, which is how `km.h` becomes
    `km.h^{-1}` and then, through the table, `\kilo\metre\per\hour`.
    '''
    def one(m: re.Match) -> str:
        body = m.group('body')
        if m.group('exponent'):
            body = f"{body}^{{{m.group('exponent')}}}"
        if m.group('degree'):
            # `$0.12\,^{\circ}\text{C}$` -- the degree sign outside the box, the letter in it.
            body = f'^\\circ {body}'
        return f'\\unit{{{body}}}' if units.lookup(body) else m.group(0)

    # 2013 puts the degree outside a box that is already a `\unit{}`: `$t_V=2^{\circ}\unit{C}$`.
    # The table knows `^\circ C` but only as one body, so fold the sign back in before the
    # match below, or the unit reads as a coulomb and the degree is left stranded in the maths.
    text = re.sub(r'\^\{?\\circ\}?\s*\\unit\{C\}', r'\\unit{^\\circ C}', text)
    return RE_UPRIGHT_UNIT.sub(one, text)
#: A literal magnitude sitting immediately before a unit, digit groups and all. The `\,` groups
#: have to be part of the match, not left behind it: `0.133\,33\unit{rad}` otherwise matched only
#: the final `33` and came out `0.133\,\qty{33}{\radian}` -- a corruption, and a silent one, since
#: a magnitude *was* found and so nothing was reported.
RE_MAGNITUDE = re.compile(
    # `10^{8}` and `8.85 \cdot 10^{-12}`, which siunitx spells `1e8` and `8.85e-12`. First,
    # because the plain form below would otherwise match the exponent's digits alone: `10^5\unit{Pa}`
    # came out `10^\qty{5}{\pascal}`, which is silent -- a magnitude was found, so nothing was
    # reported -- and wrong by five orders of magnitude.
    r'(?:(?P<mantissa>-?\d+(?:[.,]\d+)?(?:\\,\d+)*)\s*\\(?:cdot|times)\s*)?'
    r'10\^\{?(?P<exponent>-?\d+)\}?\s*$'
    # Or a plain literal. `(?<![\d.])` keeps the run maximal -- without it the regex answers a
    # *shorter* suffix rather than failing, and `\frac{74\unit{m}}{...}` came out
    # `\frac{7\qty{4}{\metre}}{...}`, the number cut in two and nothing reported. Whether the
    # run is an exponent or index is then decided in code, where the two characters before it
    # can both be looked at; a `{` alone must not disqualify it, since `\frac{74\unit{m}}` is a
    # perfectly good magnitude inside a brace.
    r'|(?<![\d.])(?P<plain>-?\d+(?:[.,]\d+)?(?:\\,\d+)*(?:\\e\{-?\d+\})?)\s*$'
    # Or that literal wrapped in a brace group of its own, which the archive writes 38 times
    # across the seven years -- `\approx{2.42}\unit{s}`. The braces did nothing even then.
    r'|\{(?P<braced>-?\d+(?:[.,]\d+)?(?:\\,\d+)*(?:\\e\{-?\d+\})?)\}\s*$')


def _is_argument(before: str, at: int) -> bool:
    r"""
    Is the group opening at `at` a macro's argument -- `\dfrac{1}{11}`, `\sqrt{2}`?

    `$d=\dfrac{1}{11}\unit{m}$` is the case this exists for. The braced literal nearest the
    unit is the *denominator*, and taking it for the magnitude produced `\dfrac{1}\qty{11}{m}`
    -- a fraction with one argument, and a number that was never a number on its own. A group
    that follows a control word is that word's first argument; one that follows another group
    is its next. Neither is a magnitude, and both are expressions, which `\qty` refuses anyway,
    so they take the "no literal magnitude" note instead.
    """
    head = before[:at].rstrip()
    return head.endswith('}') or re.search(r'\\[a-zA-Z]+$', head) is not None


def _is_script(before: str, at: int) -> bool:
    """Is the literal at `at` somebody's exponent or index -- `x^2`, `x^{12}`, `T_1`?"""
    head = before[:at]
    return head.endswith(('^', '_')) or (head.endswith('{') and head[:-1].endswith(('^', '_')))
#: `\e{8}` is the year's `\def\e#1{\cdot 10^{#1}}`. siunitx spells that natively as `5e8`, and
#: `core/latex/siunitx.tex` already sets `exponent-product = \cdot`, so it prints as it printed.
RE_E = re.compile(r'\\e\{(-?\d+)\}')


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
        if num is not None:
            # A braced literal is a script exactly when its opening brace is, so the position
            # tested is one before the digits: `x^{12}` must stay an exponent.
            at = (num.start('plain') if num.group('plain') is not None
                  else num.start('braced') - 1 if num.group('braced') is not None else None)
            if at is not None and (_is_script(before, at) or
                                   (num.group('braced') is not None
                                    and _is_argument(before, at))):
                num = None
        written = ((num.group('plain') or num.group('braced')) if num and
                   (num.group('plain') or num.group('braced')) is not None
                   else f"{num.group('mantissa') or '1'}e{num.group('exponent')}" if num else '')
        out.append(text[i:i + num.start()] if num else before)
        if num and '\\,' in written:
            # siunitx groups digits itself, from `\qty`'s own settings, so the archive's manual
            # `\,` between groups has to come out of the number.
            notes.append(f'unit: `{written}` had its digit groups spelled with `\\,`; '
                         f'siunitx groups them itself, so the number is now '
                         f'`{written.replace(chr(92) + ",", "")}`')
        magnitude = (RE_E.sub(r'e\1', written.replace('\\,', '').replace(',', '.'))
                     if num else '')
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


def exponents(text: str) -> tuple[str, list[str]]:
    r"""
    `$6\e{23}$` -> `$\num{6e23}$`, for the ones with no unit after them.

    Run after `quantities`, which has already folded `\e` into the magnitude of every `\qty` it
    built. What is left is a bare power of ten -- Avogadro's number, the answer's `1.0\e{11}` --
    and those want `\num`, so that siunitx sets the exponent rather than the author.
    """
    notes = []
    out = re.sub(r'(-?\d+(?:[.,]\d+)?)\\e\{(-?\d+)\}', r'\\num{\1e\2}', text)
    for m in RE_E.finditer(out):
        notes.append(f'exponent: `\\e{{{m.group(1)}}}` with no literal before it -- '
                     f'write the whole number by hand')
    return out, notes


#: What solutions here call their displays. `solution-unlabelled` wants every block in a solution
#: labelled -- the label is what makes pandoc number the equation -- and the repository's own
#: habit is ordinals: `third` 29 times, `fourth` 27, `second` 21, `first` 18.
ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth',
            'ninth', 'tenth', 'eleventh', 'twelfth']


#: A display, in each of the three spellings the archive uses. `align*` (12 uses) and
#: `equation*` (2) are ordinary amsmath; `$$…$$` is plain TeX. The remaining two environments
#: are left for a person: `alignat*` takes a column count and is what `|arr` is for, and `array`
#: only ever appears *inside* a display, where it stays.
RE_DISPLAY = re.compile(r'\$\$(.*?)\$\$'
                        r'|\\begin\{(align\*|flalign\*|gather\*)\}(.*?)'
                        r'\\end\{(?:align\*|flalign\*|gather\*)\}'
                        r'|\\begin\{(equation\*?)\}(.*?)\\end\{equation\*?\}'
                        r'|\\begin\{(eqnarray\*?)\}(?P<eqnarray>.*?)\\end\{eqnarray\*?\}'
                        r'|\\\[(?P<bracket>.*?)\\\]', re.S)
#: `eqnarray`'s middle column, which `aligned` does not have and does not want. `A &=& B` in an
#: `aligned` makes `B` the *right* half of an `rl` pair, so it is pushed to the right edge of its
#: column and a gap opens after the `=` as wide as the longest row needs -- exactly the failure
#: CLAUDE.md records for the 24 chemistry chains. The right spelling is `A &= B`.
RE_EQNARRAY_RELATION = re.compile(r'&\s*(=|\\approx|\\doteq|\\leq|\\geq|\\equiv|<|>)\s*&')


def wrap(text: str, width: int = 100, limit: int = 120) -> str:
    r"""
    Hard-wrap prose. 2013 is the first year whose sources are one long line per paragraph.

    2009 to 2012 were wrapped by hand at about eighty columns and the conversion simply kept
    their breaks; 2013's `TERM/rozhranie.tex` and the rest write a paragraph on one line, which
    came out as 115 lines over the 120-column limit. Pandoc runs with `--wrap=preserve`, so the
    break a source line takes is the break the TeX gets, and reflowing rendered output is
    forbidden -- which leaves the source as the only place to do it.

    Three things are never broken: a display block's body and delimiters, a `%#` marker, and a
    figure. And a line never *ends* in a backslash: `v\ istej` is a non-breaking space, so a
    break at that space would leave a bare `\` at the end of the line -- a Markdown hard line
    break, and `\hfill\break` in the TeX.

    Only a line that breaks the 120-column limit is reflowed, and it is reflowed to 100. A line
    the archive wrapped for itself is left exactly as it is, however short: 2010's longest is
    107 columns and re-breaking those would have moved text in volumes already converted and
    read, to no end.
    """
    out, display = [], False
    for line in text.split('\n'):
        stripped = line.strip()
        # `$$`, `$${`, `}$$` and the closing `$$ {#eq:…}` all delimit; everything between is a
        # formula and is never re-broken.
        if stripped.startswith('$$') or stripped.startswith('}$$'):
            display = not display
            out.append(line)
            continue
        if display or line.startswith('%#') or stripped.startswith('![') or len(line) <= limit:
            out.append(line)
            continue
        indent = line[:len(line) - len(line.lstrip())]
        # Break points are the spaces a break may fall on: not one that belongs to a `\ `.
        parts, current = [], indent
        for word in re.split(r'(?<!\\) ', line.strip()):
            if current.strip() and len(current) + 1 + len(word) > width:
                parts.append(current)
                current = indent + word
            else:
                current = f'{current} {word}' if current.strip() else current + word
        parts.append(current)
        out.extend(parts)
    return '\n'.join(out)


def displays(text: str, label_prefix: str | None = None) -> tuple[str, list[str]]:
    r"""
    Every display -> the house block form, body indented four spaces.

    An aligned block is `$${…}$$` and a single equation `$$…$$`; that is what `MathObject`'s
    `align` and `disp` emit, so a hand-written display should look like a rendered one. With
    `label_prefix` (a problem id) each gets `{#eq:<id>:<ordinal>}`, which is what
    `solution-unlabelled` asks of a solution. Statements mostly go unlabelled, so problem bodies
    are converted without one.

    Terminal punctuation is kept and reported: whether a display ends the sentence decides
    whether a blank line follows it, and only the sentence knows.
    """
    notes = []
    counter = iter(ORDINALS)

    def sub(m):
        aligned = m.group(2) is not None or m.group('eqnarray') is not None
        body = (m.group(1) if m.group(1) is not None
                else m.group(3) if m.group(2) is not None
                else m.group(5) if m.group(5) is not None
                else m.group('eqnarray') if m.group('eqnarray') is not None
                else m.group('bracket')).strip()
        if m.group('eqnarray') is not None:
            body = RE_EQNARRAY_RELATION.sub(lambda r: f'&{r.group(1)} ', body)
        punct = ''
        tail = re.search(r'\s*([.,;])\s*$', body)
        if tail:
            punct = tail.group(1)
            body = body[:tail.start()].rstrip()
            # `\ .` -- the space belonged to the escape, so rstrip left the backslash bare and
            # re-appending the stop spelled `\.`, which is a Markdown escape rather than the
            # thin space it looks like. An odd run of backslashes here was an escaped space.
            body = re.sub(r'(?<!\\)((?:\\\\)*)\\$', r'\1', body)
            notes.append(f'display: ends with `{punct}` -- check the blank line after it '
                         f'agrees (see `display-paragraph`)')
        lines = [('    ' + l.strip()) if l.strip() else '' for l in body.split('\n')]
        label = ''
        if label_prefix:
            try:
                label = f' {{#eq:{label_prefix}:{next(counter)}}}'
            except StopIteration:
                notes.append('display: more than twelve blocks -- name the rest by hand')
        # An `align*` with nothing to align is a plain display. The archive reaches for the
        # environment out of habit -- `MAT/mravce` wraps a single `&`-less row in one -- and
        # `$${…}$$` would put it through `aligned` for no reason.
        open_, close = ('$${', '}$$') if aligned and '&' in body else ('$$', '$$')
        # 2013 opens a display in the middle of a line of prose -- `\ldots platiť, že $$…$$`.
        # `$$` has to start its own line, or `display-paragraph` and the lint read the prose and
        # the opening delimiter as one line and every judgement about the break is made on it.
        head = '' if m.start() == 0 or text[m.start() - 1] == '\n' else '\n'
        # A marker rather than a newline, because the prose that follows is separated from the
        # display by the space that used to sit inside the line, and it has to go with it.
        tail = '' if m.end() >= len(text) or text[m.end()] == '\n' else '\x00'
        return head + f'{open_}\n' + '\n'.join(lines) + punct + f'\n{close}' + label + tail

    return re.sub('\x00[ \t]*', '\n', RE_DISPLAY.sub(sub, text)), notes


#: Binary operators `mdcheck` insists on having spaces around (`EqualsSpaces`, `PlusSpaces`,
#: `CdotSpaces`). The archive writes `mh+MH` and `={H(2m+3M)\over…}` freely.
#: A display, or an inline formula. Inline maths may run over a line break -- 15 of 2009's do --
#: but never over a blank line, which would mean an unmatched `$` had swallowed a paragraph.
RE_MATH = re.compile(r'\$\$.*?\$\$|\$(?:[^$\n]|\n(?!\n))*\$', re.S)
RE_RELATION = re.compile(r'\s*(\\approx|\\doteq|\\geq|\\leq|\\gg|\\ll|[=<>])\s*')
#: A `+` or `-` with something either side of it, and not the unary one that opens a group or
#: follows another operator, nor one inside a superscript like `10^{+3}` or `x^{-1}`. The
#: preceding character must be the *end* of an operand, which `{`, `^` and `_` never are.
RE_PLUS = re.compile(r'(?<=[\w}\)\]])\s*([-+])\s*(?=[\w\\{\(])')
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
            piece = RE_PLUS.sub(lambda r: f' {r.group(1)} ', piece)
            piece = RE_CDOT.sub(r' \\cdot ', piece)
            guarded[i] = piece
        return ''.join(guarded)
    return RE_MATH.sub(space, text)


def quotes(text: str) -> str:
    r"""
    `\uv{...}` -> `"..."`, which pandoc's `+smart` sets as the Slovak pair.

    `\uv` is csquotes' Czech/Slovak "uvozovky" and typesets `\u201e...\u201c`. The house convention is
    ASCII quotes in the source -- 507 of them across phys -- with pandoc making the pair, and
    `mdcheck`'s `uni` rule bans the curly characters outright. Three in 2010.
    """
    while True:
        m = re.search(r'\\uv(?![a-zA-Z])\s*(?=\{)', text)
        if not m:
            return text
        end = match_brace(text, m.end())
        text = f'{text[:m.start()]}"{text[m.end() + 1:end - 1]}"{text[end:]}'


def footnotes(text: str) -> str:
    r"""
    `\footnote{...}` -> Markdown's inline `^[...]`.

    pandoc's own spelling, and the house one: `24/signal`, `24/venus`, `23/thief-pro` and
    `23/worldbuilder` all carry one. The body is taken brace-matched, because two of the
    archive's four span several lines and contain maths.
    """
    while True:
        m = re.search(r'\\footnote(?![a-zA-Z])\s*(?=\{)', text)
        if not m:
            return text
        end = match_brace(text, m.end())
        body = ' '.join(text[m.end() + 1:end - 1].split())
        text = f'{text[:m.start()]}^[{body}]{text[end:]}'


#: siunitx macros, whose arguments are already a number and must not be wrapped again.
RE_SIUNITX = re.compile(r'\\(?:qty|num|qtylist|numlist|ang|qtyrange|numrange)'
                        r'(?:\[[^\]]*\])?\{[^}]*\}(?:\{[^}]*\})?')
#: A number siunitx should be setting rather than the author: a decimal, or a run with the
#: archive's manual `\,` between digit groups. Neither may have a digit or dot either side.
RE_DECIMAL = re.compile(r'(?<![\d.])(\d+\.\d+(?:\\,\d+)*|\d+(?:\\,\d+)+)(?![\d.])')


def decimals(text: str) -> str:
    r"""
    A bare `$0.8c$` in maths -> `$\num{0.8}c$`, so the decimal separator stays Slovak.

    `mathab.sty` made `.` active in maths and set it as a comma, so the archive's `$0.8c$`
    *printed* `0,8c`. Today the comma is siunitx's `output_decimal_marker`, which reaches only
    what siunitx sets -- so an unwrapped decimal would print a point on a page where every
    `\qty` beside it prints a comma. Found in `MAT/squash` and `TERM/decibely` by reading the
    built booklet, not by any check.

    The same applies to a digit group the archive spelled by hand: `$3\,600$` is `\num{3600}`,
    which lets `group-separator` and `group-minimum-digits` decide, as they do for every other
    number in the booklet. 2010 writes eleven of these.
    """
    def wrap(m: re.Match) -> str:
        # siunitx groups digits itself, from `\\num`'s own settings, so the archive's manual
        # `\\,` between groups comes out of the number.
        return '\\num{' + m.group(1).replace('\\,', '') + '}'

    def one(m: re.Match) -> str:
        guarded = RE_SIUNITX.split(m.group(0))
        pieces = RE_SIUNITX.findall(m.group(0))
        out = [RE_DECIMAL.sub(wrap, guarded[0])]
        for piece, rest in zip(pieces, guarded[1:]):
            out += [piece, RE_DECIMAL.sub(wrap, rest)]
        return ''.join(out)
    return RE_MATH.sub(one, text)


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
    for m in re.finditer(f'(?<![{LETTER}])([{LETTER}]{{0,3}})~', text):
        if not _tied(m.group(1)):
            notes.append(f'tie: `{text[max(0, m.start() - 12):m.end() + 12]!r}` -- a `~` that is '
                         f'not a preposition')
    for name in ('alignat*', 'enumerate', 'itemize', 'tabular', 'multipic'):
        for _ in re.finditer(r'\\begin\{' + re.escape(name) + r'\}', text):
            notes.append(f'environment: `{name}` has no mechanical translation -- `alignat*` '
                         f'is what `|arr` is for, `enumerate` and `itemize` are Markdown lists, '
                         f'`tabular` is a Markdown table, and `multipic` sets two drawings side '
                         f'by side (see `tools/ancient/compose.py`)')
    # A macro *definition* in a problem body is always bookkeeping, and always points at
    # something outside the problem. 2010's `ELEK/drotena_kocka` opens
    # `\edef\drotenakocka{\the\cislo}` so that `ELEK/elektrostavebnica` can cite its number;
    # the modern tree has no counter to read, so both halves need a person.
    for m in re.finditer(r'\\(?:e|g|x)?def\\([a-zA-Z@]+)|\\newcommand\s*\{?\\([a-zA-Z@]+)',
                         text):
        notes.append(f'macro: `\\{m.group(1) or m.group(2)}` is *defined* here -- bookkeeping '
                     f'for something outside the problem, which has no equivalent')
    for name in ('hskip', 'vskip', 'break', 'par', 'texttt', 'paragraph',
                 'multiobrazok', 'the'):
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
