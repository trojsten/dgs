r"""
What the macros meant, in the year they were used.

The archive is not one dialect but several, and the differences are silent. `\obrazok` takes two
arguments in 2009 and has no caption or label at all; four in 2010–2013, with the label third;
five in 2014–2015, with caption and label **swapped**:

    2009  \def\obrazok#1#2{\begin{center}\includegraphics[scale = #1]{#2}\end{center}}
    2013  \def\obrazok#1#2#3#4{\begin{figure}[H]\pict{#1}{#2}\caption{#4}\label{#3}\end{figure}}
    2014  \def\obrazok#1#2#3#4#5{\begin{figure}[#5]\pict{#1}{#2}\caption{#3}\label{#4}\end{figure}}

`\kmh` is `km / h` in `mathab.sty` and `km\,h^{-1}` in `2009/ulohy/include.tex`, which is loaded
afterwards and wins. A table written once and applied to every year would transpose a hundred
captions into labels and print the wrong units, and nothing would say so.

So the year's own `include.tex` is parsed, and what it says is checked against what we expect.
A mismatch is a hard error: it means this is a year nobody has looked at yet.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

#: `\def\name#1#2…{body}` -- TeX's own definition syntax, which is all these files use.
RE_DEF = re.compile(r'\\def\\([a-zA-Z@]+)((?:#\d)*)\s*\{', re.M)

#: Which argument a figure macro's body hands to `\includegraphics` or `\pict`, and which to
#: `\caption` and `\label`. `\pict{#1}{#2}` scales with the first and draws the second.
RE_DRAWS = re.compile(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{#(\d)\}'
                      r'|\\pict\s*\{#\d\}\s*\{#(\d)\}')
RE_CAPTIONS = re.compile(r'\\caption\s*\{#(\d)\}')
RE_LABELS = re.compile(r'\\label\s*\{#(\d)\}')


def figure_macro(arity: int, body: str) -> tuple[int, int, int | None, int | None] | None:
    r"""
    `(arity, file, caption, label)` for a macro that draws a figure, indices 0-based.

    Read off the definition rather than tabulated, because a year has more than one of these
    and they are not the same shape. 2014 defines `\obrazok`, `\zadobrazok` and
    `\obtekobrazok`; only the first was ever handled, so `ELEK/ikosaeder` and `ZVYS/cylinder`
    -- whose only drawing is a `\zadobrazok` -- converted with no figure at all and nothing
    said so. Returns None for a macro that draws nothing, or draws something fixed: the logos
    take no argument and are not a problem's picture.
    """
    draws = RE_DRAWS.search(body)
    if draws is None:
        return None
    file = int(draws.group(1) or draws.group(2)) - 1
    caption = RE_CAPTIONS.search(body)
    label = RE_LABELS.search(body)
    return (arity, file,
            int(caption.group(1)) - 1 if caption else None,
            int(label.group(1)) - 1 if label else None)


def definitions(path: Path) -> dict[str, tuple[int, str]]:
    """Every `\\def` in a style file, as name -> (arity, body)."""
    from tools.ancient.lex import match_brace, strip_comments
    text = strip_comments(path.read_text(encoding='utf-8', errors='replace'))
    out = {}
    for m in RE_DEF.finditer(text):
        try:
            end = match_brace(text, m.end() - 1)
        except ValueError:
            continue
        out[m.group(1)] = (len(m.group(2)) // 2, text[m.end():end - 1])
    return out


@dataclass
class Dialect:
    """One year's macro conventions, verified against that year's `include.tex`."""
    year: int
    root: Path
    #: `\obrazok`'s arity, and which argument (0-based) holds what. `None` means the year's
    #: version does not carry that piece at all -- 2009 has no caption and no label.
    figure_arity: int = 2
    figure_file: int = 1
    figure_caption: int | None = None
    figure_label: int | None = None
    defs: dict[str, tuple[int, str]] = field(default_factory=dict)
    #: Every macro in the year's `include.tex` that draws a figure -> (arity, file, caption,
    #: label). `\obrazok` is merely the one the descriptor above pins down.
    figures: dict[str, tuple[int, int, int | None, int | None]] = field(default_factory=dict)

    @classmethod
    def read(cls, root: Path, year: int) -> 'Dialect':
        include = root / 'include.tex'
        if not include.is_file():
            raise SystemExit(f'{include} does not exist; is {root} really a year of problems?')
        defs = definitions(include)

        known = {
            2009: dict(figure_arity=2, figure_file=1, figure_caption=None, figure_label=None),
            2010: dict(figure_arity=4, figure_file=1, figure_caption=3, figure_label=2),
            2011: dict(figure_arity=4, figure_file=1, figure_caption=3, figure_label=2),
            2012: dict(figure_arity=4, figure_file=1, figure_caption=3, figure_label=2),
            2013: dict(figure_arity=4, figure_file=1, figure_caption=3, figure_label=2),
            2014: dict(figure_arity=5, figure_file=1, figure_caption=2, figure_label=3),
            2015: dict(figure_arity=5, figure_file=1, figure_caption=2, figure_label=3),
        }
        if year not in known:
            raise SystemExit(
                f'{year} has no descriptor. Read {include} -- in particular the arity and '
                f'argument order of \\obrazok -- and add one; do not guess.')
        d = cls(year=year, root=root, defs=defs, **known[year])

        d.figures = {name: shape for name, (arity, body) in defs.items()
                     if (shape := figure_macro(arity, body)) is not None and arity}

        if 'obrazok' in defs:
            arity = defs['obrazok'][0]
            if arity != d.figure_arity:
                raise SystemExit(
                    f'{include} defines \\obrazok with {arity} arguments, but the descriptor for '
                    f'{year} says {d.figure_arity}. The argument order almost certainly moved '
                    f'too -- read the definition before changing the descriptor.')
            # The descriptor is the thing a person checked; the derivation is what the file
            # actually says. They have to agree, or one of them is reading the year wrongly.
            derived = d.figures.get('obrazok')
            expected = (d.figure_arity, d.figure_file, d.figure_caption, d.figure_label)
            if derived != expected:
                raise SystemExit(
                    f'{include} defines \\obrazok as {derived} (arity, file, caption, label) '
                    f'but the descriptor for {year} says {expected}. Read the definition.')
        return d

    def expansion(self, name: str) -> str | None:
        """The year's body for a zero-argument macro, e.g. `\\kmh` -> `\\mrm{km\\,h^{-1}}`."""
        entry = self.defs.get(name)
        return entry[1] if entry and entry[0] == 0 else None

    def shorthands(self) -> dict[str, str]:
        r"""
        The year's zero-argument macros that are safe to expand where they stand.

        2014 defines `\ciarka` as `\,,` and `\bodka` as `\,\text{.}` -- its own names for the
        comma and the full stop that end a display. Left unexpanded they are invisible to
        `displays`, which reads the terminal punctuation off the end of the body and decides
        from it whether a blank line follows; every one of those judgements would have been
        made on a display that appeared to end in nothing.

        Two kinds are held back. One the units table already knows -- `\kmh` is
        `\kilo\metre\per\hour` and is expanded *there*, after the `\unit{}` around it has been
        read, because expanding it first builds `\unit{\unit{…}}`. And one whose body reaches
        for a TeX primitive: 2009's `\slash` is `\delimiter"02F30E`, which means `/` and says
        so in a way nothing downstream could read. Those stay as written and are reported.
        """
        from tools.ancient import units
        primitive = re.compile(r'\\(?:delimiter|mathchar|char|hbox|vbox|kern|hskip|vskip|penalty)'
                               r'(?![a-zA-Z])')
        return {name: body for name, (arity, body) in self.defs.items()
                if arity == 0 and units.lookup(f'\\{name}') is None
                and not primitive.search(body)}
