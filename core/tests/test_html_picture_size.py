r"""
The printed size of a picture, as a web page can honour it.

`{height=30mm}` is a height, and pandoc gives LaTeX
`\includegraphics[width=\linewidth, height=30mm, keepaspectratio]` -- *fit the measure, and be
at most 30mm tall*. A web page cannot be told a bare height: on a 4:1 drawing a 60mm height
asks for 240mm of a page whose width nobody knows. Said as a **width** it says both at once,
and the picture's own proportions are what convert the one into the other -- which is why this
lives beside the file and not in the convertor.

**What bounds it is the window, not the measure.** The booklet clamps a drawing to
`\linewidth` because a page has an edge; a page that scrolls has not, so the authored height
is honoured and a wide drawing is let past the text column. `29/chopper` is 60mm tall on the
web and 45mm in the booklet, which cannot give 240mm of width to a 180mm column.
"""
import pathlib
import struct
import zlib

import pytest

from core.html import page

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
       'viewBox="0 0 {vw} {vh}"></svg>')


def write_png(path: pathlib.Path, width: int, height: int):
    def chunk(kind, body):
        return (struct.pack('>I', len(body)) + kind + body
                + struct.pack('>I', zlib.crc32(kind + body)))
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IEND', b''))


class TestAspect:
    def test_an_svg_states_it_in_its_own_units(self, tmp_path):
        picture = tmp_path / 'p.svg'
        picture.write_text(SVG.format(w='432pt', h='108pt', vw=432, vh=108))
        assert page.aspect(picture) == 4.0

    def test_a_percentage_falls_through_to_the_viewbox(self, tmp_path):
        """
        The quiet case that matters: `width="100%"` is relative to a parent this code has not
        got, so reading it as a number would give an aspect of 1 and size every such drawing
        square. The `viewBox` is always in the drawing's own units.
        """
        picture = tmp_path / 'p.svg'
        picture.write_text(SVG.format(w='100%', h='100%', vw=300, vh=200))
        assert page.aspect(picture) == 1.5

    def test_a_png_states_it_in_its_header(self, tmp_path):
        picture = tmp_path / 'p.png'
        write_png(picture, 800, 500)
        assert page.aspect(picture) == 1.6

    def test_a_format_we_do_not_read_says_so(self, tmp_path):
        """Quiet: returning None is how `size` knows to fall back, rather than inventing 1.0."""
        picture = tmp_path / 'p.webp'
        picture.write_bytes(b'RIFF....WEBP')
        assert page.aspect(picture) is None

    def test_a_truncated_file_does_not_raise(self, tmp_path):
        picture = tmp_path / 'p.png'
        picture.write_bytes(b'\x89PNG\r\n\x1a\n')
        assert page.aspect(picture) is None


class TestSize:
    @pytest.fixture
    def wide(self, tmp_path):
        picture = tmp_path / 'wide.svg'
        picture.write_text(SVG.format(w='432pt', h='108pt', vw=432, vh=108))
        return picture

    def test_a_height_becomes_the_width_it_implies(self, wide):
        """`height=60mm` on a 4:1 drawing is 240mm of width, which is what LaTeX sets too."""
        assert page.size('height:60mm', wide) == \
            'width: min(240.0mm, calc(100vw - 2rem)); height: auto'

    def test_the_width_is_the_one_the_height_implies(self, wide):
        """
        `height=30mm` on a 4:1 drawing is 120mm of width, and that is what LaTeX sets too
        wherever the column can hold it. Where it cannot, print clamps and the web does not.
        """
        assert 'min(120.0mm,' in page.size('height:30mm', wide)

    def test_an_authored_width_is_taken_as_it_stands(self, wide):
        """The quiet case: nothing to convert, so the aspect ratio is not consulted at all."""
        assert page.size('width:80mm', wide) == \
            'width: min(80.0mm, calc(100vw - 2rem)); height: auto'

    def test_an_unreadable_picture_falls_back_to_a_ceiling(self, tmp_path):
        """
        Quiet: with no aspect there is no width to compute, and a ceiling is at least never
        *too wide*. Guessing a ratio would silently distort or oversize the drawing.
        """
        picture = tmp_path / 'p.webp'
        picture.write_bytes(b'RIFF....WEBP')
        assert page.size('height:30mm', picture) == \
            'max-width: calc(100vw - 2rem); max-height: 30mm; height: auto'

    def test_no_size_at_all_is_still_bounded(self, wide):
        """LaTeX refuses an unsized picture outright; the web at least must not overflow."""
        assert page.size('', wide) == 'max-width: calc(100vw - 2rem); height: auto'
