r"""
Put a figure's labels back into text, when the conversion could only outline them.

`_from_eps` reports it when this happens: a CorelDRAW or dvips EPS embeds its fonts as Type 1
subsets with no **ToUnicode** map, so nothing downstream can say what a glyph *is*. `mutool`
then writes a row of U+FFFD and `pdftocairo` writes outlines, and the outlines are what ships,
because they at least draw the right picture. 2007 is the whole of that problem today: all 21
of its figures are CorelDRAW 11 exports and every one of them lost its text this way.

The outlines are recoverable, though, because `pdftocairo` is tidy about them. It defines each
distinct shape once,

    <g id="glyph-1-0"><path d="M 2.54 -8.09 C …"/></g>

and places it at a baseline,

    <use xlink:href="#glyph-1-0" x="14.03" y="16.34"/>

so a table naming the 92 shapes -- read once off a rendered sheet of them -- turns every
placement into a `<text>` at the coordinates the drawing already uses. Nothing moves; the
letters merely stop being outlines and become Minion Pro, which is what every other volume's
figures are set in.

    uv run python -m tools.ancient.outlines --year 2007 source/naboj/phys/10/problems

Two things the table can say. `i` or `u` is the style -- italic for a variable, upright for a
digit, a unit, an operator or a degree sign -- and `-` leaves a shape outlined, which is right
for an accent: the arrow of a `\vec{F}` belongs to the drawing and not to the label.

Figures are matched to the table by the shapes they contain rather than by filename, because a
figure is copied into the tree under the role it plays (`problem.svg`, `solution-2.svg`) and
has long since lost the archive's name for it.
"""
import argparse
import hashlib
import re
from pathlib import Path

import yaml

#: One placement. The `<g fill=…>` around it is left alone -- a `<text>` inherits the fill --
#: and more than one `<use>` may share one `<g>`, which is how `p_gula` writes its `d=?`.
RE_USE = re.compile(r'<use xlink:href="#(?P<id>glyph-\d+-\d+)" '
                    r'x="(?P<x>[-\d.]+)" y="(?P<y>[-\d.]+)"/>')
RE_DEF = re.compile(r'<g id="(?P<id>glyph-\d+-\d+)">\s*<path d="(?P<d>[^"]*)"[^>]*/>\s*</g>')


def fingerprint(svg: str) -> str:
    """What shapes this figure defines, as one hash. Two copies of a figure agree on it."""
    shapes = ''.join(m['d'] for m in RE_DEF.finditer(svg))
    return hashlib.sha256(shapes.encode()).hexdigest() if shapes else ''


def convert(svg: str, table: dict[str, list]) -> tuple[str, int]:
    """Replace every placement the table names; return the text and how many there were."""
    kept, replaced = set(), 0

    def one(m: re.Match) -> str:
        nonlocal replaced
        entry = table.get(m['id'])
        if entry is None or entry[1] == '-':
            kept.add(m['id'])
            return m.group(0)
        character, style, size = entry
        italic = ' font-style="italic"' if style == 'i' else ''
        replaced += 1
        return (f'<text x="{m["x"]}" y="{m["y"]}" font-family="Minion Pro"{italic} '
                f'font-size="{size:g}">{character}</text>')

    svg = RE_USE.sub(one, svg)
    # A shape nothing places any more is dead weight, and leaving it would make the figure
    # match its own fingerprint on a second run while having nothing left to convert.
    for m in list(RE_DEF.finditer(svg)):
        if m['id'] not in kept:
            svg = svg.replace(m.group(0), '')
    return svg, replaced


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--year', type=int, required=True)
    p.add_argument('--table', type=Path, help='default: tools/ancient/glyphs/<year>.yaml')
    p.add_argument('tree', type=Path, help="the volume's `problems/` directory")
    a = p.parse_args()

    table = a.table or Path(__file__).parent / 'glyphs' / f'{a.year}.yaml'
    named = yaml.safe_load(table.read_text())
    by_shapes = {info['shapes']: (stem, info['glyphs']) for stem, info in named.items()}

    total, touched, unknown = 0, 0, []
    for svg in sorted(a.tree.rglob('*.svg')):
        text = svg.read_text()
        mark = fingerprint(text)[:16]
        if not mark:
            continue                      # a figure with no outlines left, or none to start
        if mark not in by_shapes:
            unknown.append(str(svg))
            continue
        stem, glyphs = by_shapes[mark]
        fixed, n = convert(text, glyphs)
        if n:
            svg.write_text(fixed)
            total += n
            touched += 1
    for path in unknown:
        print(f'  no entry for {path}; its outlines are left as they are')
    print(f'{total} label(s) in {touched} figure(s) re-set in Minion Pro')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
