r"""
Cropping a drawing to its ink, which `tools/ninja/crop.py` does on a raster.

The box used to come from `pdfcrop`, which is `gs -sDEVICE=bbox` over the page's marking
operations -- and librsvg writes a gradient, an opacity or a Gaussian blur as a *full-page
image behind a soft mask*, which that device counts as a mark wherever the mask is transparent.
So a drawing with a gradient in it was never cropped at all, and one with blurs took minutes:
`29/sinking` spent 224.7 s there against rsvg-convert's 0.25. Both halves are pinned below, the
first because it is the one a reader would call a cosmetic difference and it is not.

The parser and the box arithmetic are exercised on bytes and arrays, so they need nothing
installed; the two conversions need poppler and librsvg and say so.
"""
import pathlib
import re
import shutil
import subprocess

import numpy as np
import pytest

from tools.ninja.crop import crop, ink_box, measure, read_pgm

needs_tools = pytest.mark.skipif(
    not (shutil.which('rsvg-convert') and shutil.which('pdftoppm') and shutil.which('pdfinfo')),
    reason='librsvg and poppler are needed to convert and measure a picture')

#: A 40x40 mark on a 200x100 canvas, 50 from the left and 20 from the top.
SHAPE = '<rect x="50" y="20" width="40" height="40" fill="black"/>'
#: The same square, painted with a gradient -- which is what librsvg turns into a full-page
#: image and a soft mask, and therefore the case `pdfcrop` could not crop.
GRADIENT = ('<defs><linearGradient id="g"><stop offset="0" stop-color="#000"/>'
            '<stop offset="1" stop-color="#888"/></linearGradient></defs>'
            '<rect x="50" y="20" width="40" height="40" fill="url(#g)"/>')


def drawing(directory: pathlib.Path, body: str) -> pathlib.Path:
    path = directory / 'drawing.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink='
                    '"http://www.w3.org/1999/xlink" width="200pt" height="100pt" '
                    f'viewBox="0 0 200 100">{body}</svg>')
    return path


def convert(svg: pathlib.Path) -> pathlib.Path:
    """`svg_pdf`'s first half, exactly as `tools/ninja/generate.py` invokes it."""
    pdf = svg.with_suffix('.pdf')
    subprocess.run(['rsvg-convert', '--format', 'pdf', '--keep-aspect-ratio',
                    '--output', str(pdf), str(svg)], check=True, capture_output=True)
    return pdf


def page(pdf: pathlib.Path) -> tuple[float, float]:
    reported = subprocess.run(['pdfinfo', str(pdf)], check=True, capture_output=True, text=True)
    found = re.search(r'Page size:\s+([\d.]+) x ([\d.]+) pts', reported.stdout)
    return float(found.group(1)), float(found.group(2))


def pgm(width: int, height: int, pixels: bytes, header: bytes = b'') -> bytes:
    return b'P5\n' + header + f'{width} {height}\n255\n'.encode() + pixels


class TestReadingTheRaster:
    def test_it_reads_width_height_and_the_pixels(self):
        raster = read_pgm(pgm(3, 2, bytes([0, 1, 2, 3, 4, 5])))
        assert raster.shape == (2, 3)
        assert raster.tolist() == [[0, 1, 2], [3, 4, 5]]

    def test_a_comment_in_the_header_is_skipped(self):
        """The format allows one anywhere in the header; poppler writes none, another tool may."""
        raster = read_pgm(pgm(2, 1, bytes([7, 8]), header=b'# written by something\n'))
        assert raster.tolist() == [[7, 8]]

    def test_a_pixel_that_happens_to_be_a_space_is_still_a_pixel(self):
        """Exactly one whitespace byte ends the header, and 0x20 is a legal grey value."""
        assert read_pgm(pgm(2, 1, b'  ')).tolist() == [[32, 32]]

    def test_it_refuses_a_raster_it_cannot_read(self):
        with pytest.raises(ValueError, match='not a binary PGM'):
            read_pgm(b'P2\n2 1\n255\n0 0\n')
        with pytest.raises(ValueError, match='maxval'):
            read_pgm(b'P5\n2 1\n65535\n' + bytes(4))


class TestFindingTheInk:
    @staticmethod
    def page_of(width=10, height=6):
        return np.full((height, width), 255, dtype=np.uint8)

    def test_a_blank_page_has_no_box(self):
        assert ink_box(self.page_of()) is None

    def test_the_box_is_half_open_so_the_last_pixel_is_inside_it(self):
        pixels = self.page_of()
        pixels[2:4, 3:7] = 0
        assert ink_box(pixels) == (3, 2, 4, 2)

    def test_one_pixel_of_ink_is_one_pixel_wide(self):
        pixels = self.page_of()
        pixels[5, 9] = 0
        assert ink_box(pixels) == (9, 5, 1, 1)

    def test_a_hairline_a_shade_off_white_is_ink(self):
        """Antialiasing is how a thin line reaches the page; 254 is a mark, not a tolerance."""
        pixels = self.page_of()
        pixels[1, 1] = 254
        assert ink_box(pixels) == (1, 1, 1, 1)

    def test_ink_against_the_edges_gives_the_whole_page(self):
        pixels = self.page_of()
        pixels[0, 0] = pixels[-1, -1] = 0
        assert ink_box(pixels) == (0, 0, 10, 6)


@needs_tools
class TestCroppingADrawing:
    def test_it_measures_the_ink_and_not_the_canvas(self, tmp_path):
        assert measure(convert(drawing(tmp_path, SHAPE))) == (50.0, 20.0, 40.0, 40.0)

    def test_the_cropped_page_is_the_ink_box(self, tmp_path):
        svg = drawing(tmp_path, SHAPE)
        pdf = convert(svg)
        assert page(pdf) == (200.0, 100.0)
        assert crop(svg, pdf) is True
        assert page(pdf) == (40.0, 40.0)

    def test_a_gradient_is_cropped_too(self, tmp_path):
        """
        The regression. librsvg paints this as a full-page image behind a soft mask, so
        `gs -sDEVICE=bbox` called the whole 200x100 canvas ink and `pdfcrop` cropped nothing.

        A point wider than the flat square, and that point is real: the mask is an image, and
        resampling it spreads the edge about a tenth of a point past the rectangle -- 40.32 at
        300 dpi against the nominal 40. Measuring the page is what finds that; measuring the
        marks found the whole canvas.
        """
        svg = drawing(tmp_path, GRADIENT)
        pdf = convert(svg)
        assert crop(svg, pdf) is True
        assert page(pdf) == (41.0, 40.0)

    def test_a_drawing_that_already_fits_is_left_alone(self, tmp_path):
        svg = drawing(tmp_path, '<rect x="0" y="0" width="200" height="100" fill="black"/>')
        pdf = convert(svg)
        before = pdf.read_bytes()
        assert crop(svg, pdf) is False
        assert pdf.read_bytes() == before

    def test_an_empty_drawing_is_left_alone_rather_than_failing(self, tmp_path):
        """A blank picture is a source defect, and not one worth stopping a booklet for."""
        svg = drawing(tmp_path, '')
        pdf = convert(svg)
        assert measure(pdf) is None
        assert crop(svg, pdf) is False
        assert page(pdf) == (200.0, 100.0)
