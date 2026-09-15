r"""
Put two of the archive's figures side by side in one SVG.

    uv run python -m tools.ancient.compose --gap 24 --labels '(1)' '(2)' \
        -o bat-echo-solution.svg netopier-ries1.svg netopier-ries2.svg

The archive sometimes sets two drawings as one figure, with plain TeX between them:
`KIN/netopier` writes `\includegraphics{...ries1.eps}\hskip4cm\includegraphics{...ries2.eps}`
and then `\par(1) \hskip 8 cm (2)` underneath. Markdown has no spelling for that -- two
`![](...)` are two figures, with the page free to break between them and only one of them
carrying the label the prose refers to -- so the two become one file here instead.

Nested `<svg>` rather than a transform: each child keeps its own coordinate system untouched,
so nothing inside has to be rewritten and the composition cannot disturb a drawing's metrics.
The labels are set in Minion Pro, matching every other label in the volume after the font pass.
"""
import argparse
import re
from pathlib import Path

RE_ROOT = re.compile(r'<svg\b[^>]*>', re.S)
RE_DIMENSION = re.compile(r'\b(width|height)="([\d.]+)(?:px)?"')
#: An `xmlns:foo="..."` on a child's root. These have to be hoisted onto the wrapper: the
#: drawings are full of `inkscape:` and `sodipodi:` attributes, and a nested `<svg>` inherits
#: its prefixes from the document, not from the file the element came out of. Without them a
#: parser stops at `Namespace prefix inkscape for stockid on marker is not defined`.
RE_NAMESPACE = re.compile(r'xmlns:[A-Za-z][\w.-]*="[^"]*"')
#: An `id="..."` and the two ways SVG points at one. Both of `KIN/netopier`'s panes were saved
#: from the same drawing, so their internal ids are identical -- `id="svg2433"` in both -- and
#: inlining them side by side made every reference in the second pane resolve to the *first*
#: pane's element. The symptom is a piece of one drawing appearing in the other's coordinates:
#: pane 2's second wavefront was being drawn from pane 1's path, a stray arc in the gap. So
#: every id is prefixed per pane before the bodies meet.
RE_ID = re.compile(r'\bid="([^"]*)"')
RE_REFERENCE = re.compile(r'(url\(#|xlink:href="#|href="#)([^)"]*)')

#: Room under the drawings for a label, and the size to set it at. Both are in the user units
#: the archive's figures are drawn in, where a drawing is about 100 tall.
LABEL_SPACE = 18.0
LABEL_SIZE = 12.0
#: The drawings overrun their own declared height by about two units -- arrowheads, which
#: Inkscape did not count -- so the box is given that back.
BLEED = 3.0


def dimensions(svg: str) -> tuple[float, float]:
    """The declared width and height of an SVG root, in user units."""
    root = RE_ROOT.search(svg)
    if not root:
        raise SystemExit('no <svg> root element')
    found = dict(RE_DIMENSION.findall(root.group(0)))
    if 'width' not in found or 'height' not in found:
        raise SystemExit(f'root declares no width/height: {root.group(0)[:120]}')
    return float(found['width']), float(found['height'])


def body(svg: str, prefix: str) -> str:
    """
    Everything inside the root element, with every internal id put under `prefix`.

    Both the id and the things that point at it, since an unprefixed reference would then find
    nothing and the element would simply not draw.
    """
    root = RE_ROOT.search(svg)
    inner = svg[root.end():svg.rfind('</svg>')]
    inner = RE_ID.sub(lambda m: f'id="{prefix}{m.group(1)}"', inner)
    return RE_REFERENCE.sub(lambda m: f'{m.group(1)}{prefix}{m.group(2)}', inner)


def compose(sources: list[str], labels: list[str], gap: float) -> str:
    sizes = [dimensions(s) for s in sources]
    width = sum(w for w, _ in sizes) + gap * (len(sources) - 1)
    height = max(h for _, h in sizes) + BLEED + (LABEL_SPACE if any(labels) else 0)

    prefixes = {'xmlns:xlink="http://www.w3.org/1999/xlink"'}
    for source in sources:
        prefixes |= set(RE_NAMESPACE.findall(RE_ROOT.search(source).group(0)))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" {" ".join(sorted(prefixes))}'
             f' width="{width:g}" height="{height:g}" viewBox="0 0 {width:g} {height:g}">']
    x = 0.0
    for index, (source, (w, h), label) in enumerate(zip(sources, sizes, labels)):
        # A `clipPath`, not the `overflow="hidden"` the SVG spec already implies for a nested
        # viewport: librsvg honours neither the implied value nor an explicit one, and
        # `KIN/netopier_ries1` carries a dashed arc drawn past its own right edge. On its own
        # that file's canvas cuts the arc off; unclipped here it floats in the gap between the
        # two drawings, belonging to neither.
        parts.append(f'<clipPath id="pane{index}">'
                     f'<rect x="0" y="0" width="{w:g}" height="{h + BLEED:g}"/></clipPath>')
        parts.append(f'<svg x="{x:g}" y="0" width="{w:g}" height="{h + BLEED:g}"'
                     f' viewBox="0 0 {w:g} {h + BLEED:g}">'
                     f'<g clip-path="url(#pane{index})">{body(source, f"p{index}-")}</g></svg>')
        if label:
            parts.append(f'<text x="{x + w / 2:g}" y="{height - LABEL_SIZE / 3:g}"'
                         f' text-anchor="middle"'
                         f' style="font-style:normal;font-size:{LABEL_SIZE:g}px;'
                         f"font-family:'Minion Pro';"
                         f'-inkscape-font-specification:&apos;Minion Pro, Normal&apos;;'
                         f'fill:#000000">{label}</text>')
        x += w + gap
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('sources', nargs='+', type=Path)
    p.add_argument('-o', '--out', type=Path, required=True)
    p.add_argument('--gap', type=float, default=24.0, help='user units between the drawings')
    p.add_argument('--labels', nargs='*', default=[], help='one caption per drawing, or none')
    a = p.parse_args()

    labels = a.labels or [''] * len(a.sources)
    if len(labels) != len(a.sources):
        raise SystemExit(f'{len(a.sources)} drawings but {len(labels)} labels')
    a.out.write_text(compose([s.read_text(encoding='utf-8') for s in a.sources], labels, a.gap),
                     encoding='utf-8')
    print(f'{len(a.sources)} drawings -> {a.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
