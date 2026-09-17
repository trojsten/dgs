"""
Identifying the glyphs that no table can decode, by looking at them.

The maths fonts in these booklets are subset with glyph names that are *indices*, not
character codes: in one formula of `08.pdf`, `=` is `G39`, `1` is `G129` and `0` is `G102`,
all in the same font. There is no constant, so no table can be written from the outside.

But there are only 171 distinct glyphs in a whole booklet, against 2637 placements of them.
So the cost is not per formula, it is **once per glyph**: crop one specimen of each, montage
them onto a sheet, read the sheet, and the entire year decodes exactly thereafter.

This is the technique `tools/ancient/glyphs/2007.yaml` already established for the 2007
figures -- 92 identifications read off a contact sheet -- applied to type instead of drawings.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from tools.ancient.pdf import encodings, glyphs

#: Rendered at this resolution a 10pt glyph is about 40px tall, which is legible on a sheet
#: without making the sheet enormous.
DPI = 300


@dataclass(frozen=True)
class Specimen:
    """One placement of one glyph, good enough to crop and look at."""
    font: str
    number: int
    page: int
    x: float
    y: float
    adv: float
    size: float
    count: int
    #: Whether the page this specimen sits on is printed on its side. `glyphs._numbers` maps a
    #: rotated page into the upright space everything downstream assumes, so a crop has to
    #: undo that mapping to find the glyph again on the paper.
    rotated: bool = False


def collect(pdf: Path, roles: set[str] | None = None) -> list[Specimen]:
    """
    One specimen of every distinct glyph whose code cannot be decoded.

    Ordered by how often the glyph occurs, so the sheet starts with the characters that
    matter most and a partial reading is still worth having.
    """
    roles = roles or (set(encodings.TABLES) | {'symbol', 'unknown'}) - {'t1'}
    pages = int(subprocess.run(['mutool', 'info', str(pdf)], capture_output=True, text=True)
                .stdout.split('Pages: ')[1].split()[0])
    best: dict[tuple[str, int], Specimen] = {}
    counts: dict[tuple[str, int], int] = {}
    for page in range(1, pages + 1):
        raw = glyphs.trace(pdf, page)
        turned = glyphs.page_rotated(raw)
        for font, n, _uni, x, y, adv, size in glyphs._numbers(raw):
            role, _ = encodings.classify(font)
            if n is None or role not in roles:
                continue
            key = (font, n)
            counts[key] = counts.get(key, 0) + 1
            if key not in best:
                best[key] = Specimen(font, n, page, x, y, adv * size, size, 0, turned)
    return sorted((Specimen(s.font, s.number, s.page, s.x, s.y, s.adv, s.size,
                            counts[k], s.rotated)
                   for k, s in best.items()),
                  key=lambda s: (s.font, -s.count))


def crop(pdf: Path, spec: Specimen, out: Path, dpi: int = DPI) -> Path:
    """
    Cut one glyph out of its page.

    `pdftocairo` takes a pixel box, so the glyph's point coordinates are scaled by dpi/72 and
    the baseline is flipped -- PDF measures y upward from the foot of the page, the raster
    downward from its head. Generous margins: an accent or a descender that falls outside the
    crop is a glyph identified wrongly.
    """
    scale = dpi / 72.0
    # Glyph coordinates come out of `glyphs.read_page` in device space with y negated, so that
    # larger means higher up. The raster measures y downward from the head of the page, which
    # is exactly the un-negated device value -- no page height involved, and none assumed.
    #
    # Tight to the glyph's own advance: a generous box shows the neighbours too, and then the
    # sheet asks which of three characters the label refers to, which is how a contact sheet
    # produces confident wrong answers.
    pad = spec.size * 0.06
    if spec.rotated:
        # `_numbers` turned this page a quarter turn to put it in the upright space, by
        # `(x, y) = (-device_y, -device_x)`. Undo exactly that: the baseline runs *up* the
        # paper, so the advance is a height and the glyph's own body is a width.
        x0 = (-spec.y - spec.size * 0.95) * scale
        y0 = (-spec.x - spec.adv - pad) * scale
        w = (spec.size * 1.35) * scale
        h = (spec.adv + 2 * pad) * scale
    else:
        x0 = (spec.x - pad) * scale
        y0 = (-spec.y - spec.size * 0.95) * scale
        w = (spec.adv + 2 * pad) * scale
        h = (spec.size * 1.35) * scale
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['pdftocairo', '-png', '-r', str(dpi), '-f', str(spec.page), '-l', str(spec.page),
         '-x', str(int(x0)), '-y', str(int(y0)), '-W', str(max(int(w), 8)),
         '-H', str(max(int(h), 8)), '-singlefile', str(pdf), str(out.with_suffix(''))],
        check=True, capture_output=True)
    if spec.rotated:
        # Set the tile back on its feet, or the sheet asks to be read sideways -- which is how
        # a `2` and a `-` become indistinguishable.
        subprocess.run(['magick', str(out), '-rotate', '90', str(out)],
                       check=True, capture_output=True)
    return out


def sheet(pdf: Path, out: Path, font_filter: str | None = None, dpi: int = DPI) -> list[Specimen]:
    """
    A labelled contact sheet of every unidentified glyph, for one sitting's reading.

    Each cell is captioned with the font stem and glyph number, which is the key the table
    will be written against, so the sheet can be read straight into a YAML file without
    counting positions -- the mistake `glyphs/2007.yaml` warns about.
    """
    specs = [s for s in collect(pdf)
             if font_filter is None or font_filter in s.font]
    tiles = []
    tmp = out.parent / '_tiles'
    for i, s in enumerate(specs):
        stem = s.font.split('+')[-1]
        tile = tmp / f'{i:04d}.png'
        crop(pdf, s, tile, dpi)
        label = f'{stem[:6]} G{s.number} x{s.count}'
        subprocess.run(
            ['magick', str(tile), '-background', 'white', '-gravity', 'center',
             '-extent', '150x150', '-bordercolor', '#bbb', '-border', '1',
             '-gravity', 'south', '-pointsize', '15', '-fill', '#0a0a0a',
             '-annotate', '+0+2', label, str(tile)], check=True, capture_output=True)
        tiles.append(str(tile))
    if tiles:
        subprocess.run(['magick', 'montage', *tiles, '-tile', '8x', '-geometry', '+2+2',
                        '-background', 'white', str(out)], check=True, capture_output=True)
    return specs
