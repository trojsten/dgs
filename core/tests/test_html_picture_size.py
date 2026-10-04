r"""
The printed size of a picture, as a web page can honour it.

`{height=30mm}` is a height, and pandoc gives LaTeX
`\includegraphics[width=\linewidth, height=30mm, keepaspectratio]` -- *fit the measure, and be
at most 30mm tall*. The web has no `\linewidth` and cannot be told a bare height either: on a
4:1 drawing a 60mm height asks for 240mm of a page whose width nobody knows.

Saying it as a **width** says both at once. `width: min(100%, 46.5mm); height: auto` is the
same sentence, with `100%` where `\linewidth` was -- the printed size wherever there is room
and a proportional shrink where there is not.

Converting one into the other needs the picture's own proportions, which is why this lives
beside the file and not in the convertor.
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
        assert page.size('height:60mm', wide) == 'width: min(100%, 240.0mm); height: auto'

    def test_it_matches_what_pandoc_tells_latex(self, wide):
        """
        `width=\\linewidth, height=30mm, keepaspectratio` is `min(linewidth, 30mm * aspect)`
        wide. The CSS has to be the same sentence or the booklet and the page disagree.
        """
        printed_width = 30.0 * 4.0
        assert f'min(100%, {printed_width:.1f}mm)' in page.size('height:30mm', wide)

    def test_an_authored_width_is_taken_as_it_stands(self, wide):
        """The quiet case: nothing to convert, so the aspect ratio is not consulted at all."""
        assert page.size('width:80mm', wide) == 'width: min(100%, 80.0mm); height: auto'

    def test_an_unreadable_picture_falls_back_to_a_ceiling(self, tmp_path):
        """
        Quiet: with no aspect there is no width to compute, and a ceiling is at least never
        *too wide*. Guessing a ratio would silently distort or oversize the drawing.
        """
        picture = tmp_path / 'p.webp'
        picture.write_bytes(b'RIFF....WEBP')
        assert page.size('height:30mm', picture) == 'max-width: 100%; max-height: 30mm; height: auto'

    def test_no_size_at_all_is_still_bounded(self, wide):
        """LaTeX refuses an unsized picture outright; the web at least must not overflow."""
        assert page.size('', wide) == 'max-width: 100%; height: auto'
