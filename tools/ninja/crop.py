r"""
Crop a drawing's PDF to its ink -- `pdfcrop`'s job, done without Ghostscript.

`pdfcrop` asks `gs -sDEVICE=bbox` where the marks are, and that device walks the page's
*marking operations*. A drawing made of flat vectors costs nothing; a drawing with a filter in
it costs minutes, because librsvg cannot express a Gaussian blur in PDF and writes each blurred
object as a transparency group behind a soft mask instead. `29/sinking` has 86 of them and its
`pdfcrop` ran for **224.7 seconds** against rsvg-convert's 0.25; its solution drawing had not
finished after 216. That is not a slow build, it is a drawing nobody can afford to use -- and it
made blurs and the gradients beside them effectively unavailable to whoever draws these.

So the box is **measured on a raster instead of on the marks**, which is a different question
with the same answer: poppler renders the page once, and the ink is the pixels that are not
white. Rendering is what a blur is cheap in -- it is a convolution the renderer does anyway --
so the pathological file costs 0.78 s rather than 224.7, and an ordinary one costs about 40 ms.

**The page is then re-converted from the source, not rewritten.** Changing a PDF's `/MediaBox`
in place needs a PDF library, and this repository has none; re-rendering the same SVG onto a
smaller page is the same drawing at the same scale with a different page box, and it costs one
more rsvg-convert. Hence the source is an argument: the crop is a *conversion*, and the thing
converted has to be to hand.

**One pixel per point, deliberately.** `pdfcrop` rounds its box outward to whole points unless
it is asked for `--hires`, so a 72 dpi raster is exactly as precise as what it replaces, and the
raster's own quantisation does the outward rounding for free: a pixel is ink if anything at all
marked it. Cost grows with the square of the resolution and precision does not, 300 dpi costing
10 s on the file this exists for.

What it is not: a general PDF cropper. It takes the pair -- the source a renderer can re-render
and the PDF that came out of it -- and is wired into `svg_pdf` in `tools/ninja/generate.py`.
"""
import argparse
import pathlib
import re
import subprocess
import sys

import numpy as np

#: One pixel per point. See the module docstring: this is `pdfcrop`'s own precision.
RESOLUTION = 72
#: A pixel is ink unless it is pure white. The threshold is deliberately *not* a tolerance --
#: an antialiased hairline reaches the page as a pixel a few values off white, and dropping it
#: would crop away the very edge of a drawing that is nothing but hairlines.
WHITE = 255


def read_pgm(data: bytes) -> np.ndarray:
    """
    The `P5` raster `pdftoppm -gray` writes to stdout, as a `height x width` array.

    Written out rather than taken from a library because the only image library here would be
    one added for this, and the format is a magic number, three integers and the bytes. The
    parser has to honour `#` comments and arbitrary whitespace between the fields, both of
    which the format allows anywhere in the header, even though poppler writes neither.
    """
    if data[:2] != b'P5':
        raise ValueError(f'not a binary PGM: {data[:16]!r}')
    fields, offset = [], 2
    while len(fields) < 3:
        if data[offset:offset + 1].isspace():
            offset += 1
        elif data[offset:offset + 1] == b'#':
            offset = data.index(b'\n', offset)
        else:
            start = offset
            while not data[offset:offset + 1].isspace():
                offset += 1
            fields.append(int(data[start:offset]))
    width, height, maximum = fields
    if maximum != 255:
        raise ValueError(f'expected an 8-bit raster, got maxval {maximum}')
    # One whitespace byte separates the header from the pixels, and exactly one: the next byte
    # is already a pixel and may legitimately be 0x20.
    return np.frombuffer(data, dtype=np.uint8, count=width * height, offset=offset + 1
                         ).reshape(height, width)


def ink_box(pixels: np.ndarray) -> tuple[int, int, int, int] | None:
    """
    `(left, top, width, height)` in pixels, or `None` for a page with nothing on it.

    Half-open on the right and the bottom, as a slice is, so `width` is the count of columns
    and not the index of the last one -- which is the off-by-one that would shave the rightmost
    pixel off every drawing.
    """
    ink = pixels < WHITE
    rows, columns = np.flatnonzero(ink.any(axis=1)), np.flatnonzero(ink.any(axis=0))
    if not rows.size:
        return None
    return (int(columns[0]), int(rows[0]),
            int(columns[-1]) - int(columns[0]) + 1, int(rows[-1]) - int(rows[0]) + 1)


def page_size(pdf: pathlib.Path) -> tuple[float, float]:
    """
    The page in points, **asked of poppler**: `272a83f`'s rule, and for its reason.

    A regex over the bytes finds `/MediaBox` only while cairo writes the page dictionary as a
    plain object; from 1.17 it writes it into a compressed object stream and the regex finds
    nothing at all.
    """
    reported = subprocess.run(['pdfinfo', str(pdf)], check=True, capture_output=True, text=True)
    found = re.search(r'Page size:\s+([\d.]+) x ([\d.]+) pts', reported.stdout)
    if not found:
        raise ValueError(f'pdfinfo reported no page size for {pdf}:\n{reported.stdout}')
    return float(found.group(1)), float(found.group(2))


def measure(pdf: pathlib.Path, resolution: int = RESOLUTION, size: tuple | None = None
            ) -> tuple[float, float, float, float] | None:
    """
    The ink box in **points**, clamped to the page, or `None` if the page is blank.

    `size` is the page, for a caller that has already asked; it is only ever used to clamp.
    """
    raster = subprocess.run(
        ['pdftoppm', '-gray', '-r', str(resolution), '-singlefile', str(pdf)],
        check=True, capture_output=True).stdout
    box = ink_box(read_pgm(raster))
    if box is None:
        return None
    scale = 72.0 / resolution
    left, top, width, height = (value * scale for value in box)
    # The raster is whole pixels and the page is not, so the last row and column of a page
    # whose size is not an integer reach a hair past its edge. Clamping keeps a crop a crop --
    # and makes a drawing that fills its canvas measure as exactly the canvas, which is what
    # `crop` tests to decide that there is nothing to do.
    page_width, page_height = size or page_size(pdf)
    return (left, top, min(width, page_width - left), min(height, page_height - top))


def crop(source: pathlib.Path, pdf: pathlib.Path, resolution: int = RESOLUTION) -> bool:
    """
    Re-render `source` onto its own ink box. True if it moved, False if it already fitted.

    The second conversion is skipped where the box *is* the page, which is most drawings in
    this repository -- a hand-drawn SVG is usually saved with the canvas already around the
    drawing -- so the common case costs one raster and nothing else.
    """
    size = page_size(pdf)
    box = measure(pdf, resolution, size)
    if box is None:
        print(f'{pdf}: nothing is drawn on the page, leaving it as it is', file=sys.stderr)
        return False
    left, top, width, height = box
    if (left, top) == (0.0, 0.0) and (width, height) == size:
        return False
    subprocess.run(
        ['rsvg-convert', '--format', 'pdf',
         # The `=` is not a style: this parser reads a bare `-3.84pt` as a flag and refuses it.
         f'--page-width={width}pt', f'--page-height={height}pt',
         f'--left={-left}pt', f'--top={-top}pt',
         '--output', str(pdf), str(source)],
        check=True)
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('source', type=pathlib.Path, help='the SVG the PDF was rendered from')
    parser.add_argument('pdf', type=pathlib.Path, help='that PDF, cropped in place')
    parser.add_argument('-r', '--resolution', type=int, default=RESOLUTION,
                        help=f'the raster the box is measured on, in dpi (default {RESOLUTION})')
    args = parser.parse_args(argv)
    crop(args.source, args.pdf, args.resolution)
    return 0


if __name__ == '__main__':
    sys.exit(main())
