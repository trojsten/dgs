r"""
A picture on the web, and the two ways one is made.

Most pictures are converted from the PDF the LaTeX path already built, so the only way the web
one and the printed one can differ is the conversion -- which is how a hairline plot came to
show as a fat curve inside a heavy black box, `dvisvgm --pdf` having invented `stroke-width=4`
for a figure whose PDF sets nothing but `0.25 w` and `0.5 w`.

A gnuplot plot skips that and is drawn twice by gnuplot, once per terminal. What can go wrong
there is that the two terminals are configured differently and the plot comes out a different
size or a different shape -- `pdfcairo` hides a `fontscale 0.5`, and the `svg` terminal counts
in pixels and lets `fontscale` move the glyphs without moving the layout. Both halves are
pinned below, by measuring rather than by looking.
"""
import pathlib
import re
import shutil
import subprocess
import zlib

import pytest

needs_tools = pytest.mark.skipif(
    not (shutil.which('gnuplot') and shutil.which('pdftocairo')),
    reason='gnuplot and pdftocairo are needed to convert a picture')

#: Two widths, one of them deliberately fat, so a conversion that merely clamped would fail too.
#: Sized the way a `.gp` in the sources is: in points, through the build's `gppt`.
PLOT = """set terminal @gpterm size 288*gppt, 144*gppt
unset key
set border linewidth 0.5
set ylabel "f / Hz"
plot x with lines linewidth 6, -x with lines linewidth 0.5
"""

#: What `Makefile`'s `GNUPLOT_PDF` and `GNUPLOT_SVG` say, which is the thing under test.
TERMINALS = {
    'pdf': ("set macros; gppt = 1.0 / 72; gpterm = 'pdfcairo fontscale 1 font \"Minion Pro, 6\"'",
            'set terminal @gpterm size 5, 3'),
    'svg': ("set macros; gppt = 4.0 / 3;  gpterm = 'svg font \"Minion Pro, 8\"'",
            'set terminal @gpterm size 480, 288'),
}

#: CSS pixels to points. The `svg` terminal counts 96 to the inch and `pdfcairo` 72.
PX = 0.75


def draw(directory: pathlib.Path, kind: str) -> pathlib.Path:
    """One plot through one terminal, exactly as the Makefile invokes it."""
    out = directory / f'plot.{kind}'
    script = directory / 'plot.gp'
    script.write_text(PLOT)
    define, terminal = TERMINALS[kind]
    subprocess.run(
        ['gnuplot', '-e', define,
         '-e', f"{terminal}; set output '{out.name}'; set fit quiet;", script.name],
        cwd=directory, check=True, capture_output=True)
    assert out.is_file()
    return out


def widths_in_pdf(pdf: pathlib.Path) -> set[str]:
    """Every `w` operator in the content stream, which is what the page is drawn with."""
    raw = pdf.read_bytes()
    found = set()
    for match in re.finditer(rb'stream\r?\n', raw):
        chunk = raw[match.end():raw.find(b'endstream', match.end())]
        try:
            text = zlib.decompress(chunk).decode('latin-1')
        except (zlib.error, UnicodeDecodeError):
            continue
        found |= {f'{float(w):g}' for w in re.findall(r'([\d.]+) w\b', text)}
    return found


def widths_in_svg(svg: pathlib.Path) -> set[str]:
    return {f'{float(w):g}'
            for w in re.findall(r"stroke-width[:=]['\"]?([\d.]+)", svg.read_text())}


@pytest.fixture
def plotted(tmp_path):
    """A gnuplot PDF, which is what every `.gp` in the sources becomes on its way to print."""
    return draw(tmp_path, 'pdf')


@needs_tools
class TestTheWebPictureIsThePrintedOne:
    def test_the_widths_are_the_pdf_s(self, plotted, tmp_path):
        """The regression: no width may appear in the SVG that the PDF never asked for."""
        svg = tmp_path / 'plot.svg'
        subprocess.run(['pdftocairo', '-svg', str(plotted), str(svg)],
                       check=True, capture_output=True)
        invented = widths_in_svg(svg) - widths_in_pdf(plotted)
        assert not invented, f'the conversion invented stroke widths: {sorted(invented)}'

    def test_a_thick_line_stays_thick(self, plotted, tmp_path):
        """
        The quiet case. `linewidth 6` is an author's choice and has to survive -- a conversion
        that passed the test above by flattening every width to a hairline would be just as
        wrong, in the other direction.
        """
        svg = tmp_path / 'plot.svg'
        subprocess.run(['pdftocairo', '-svg', str(plotted), str(svg)],
                       check=True, capture_output=True)
        widths = {float(w) for w in widths_in_svg(svg)}
        assert max(widths) >= 2, f'the thick line was flattened: {sorted(widths)}'
        assert min(widths) < 1, f'the hairline was thickened: {sorted(widths)}'


@needs_tools
class TestGnuplotDrawsTheSamePlotTwice:
    """
    A `.gp` is drawn by gnuplot for print and for the web, so nothing converts between them and
    the only thing that can differ is how the two terminals were set up. Twice now it has been
    set up wrongly, in both directions, and both times the plot *rendered* -- it was merely a
    different picture. So this measures.
    """

    @staticmethod
    def canvas(path: pathlib.Path) -> tuple[float, float]:
        if path.suffix == '.svg':
            found = re.search(r'width="([\d.]+)"\s+height="([\d.]+)"', path.read_text())
        else:                                           # a PDF's MediaBox, in points
            found = re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)',
                              path.read_bytes())
            return tuple(float(x) for x in found.groups())
        return tuple(float(x) for x in found.groups())

    def test_the_canvas_is_the_same_physical_size(self, tmp_path):
        """
        `288*gppt, 144*gppt` has to be 288 by 144 **points** in both, which is what `gppt` is
        for: `pdfcairo` reads a bare number as inches, the `svg` terminal as CSS pixels and
        rejects `cm` outright. Get it wrong and the web picture is the right shape at the
        wrong size -- a quarter small, which is what dropping the 96/72 did.
        """
        for kind in ('pdf', 'svg'):
            (tmp_path / kind).mkdir()
        assert self.canvas(draw(tmp_path / 'pdf', 'pdf')) == (288.0, 144.0)
        width, height = self.canvas(draw(tmp_path / 'svg', 'svg'))
        assert (width * PX, height * PX) == (288.0, 144.0)

    def test_the_type_is_the_same_size_in_both(self, tmp_path):
        """
        The one that bit twice. `pdfcairo` defaults to `fontscale 0.5`, so `font "…, 12"` sets
        6pt; the `svg` terminal has no such halving, and its `fontscale` scales the glyphs
        without scaling the space reserved for them, so it cannot be used to match. The build
        passes `fontscale 1` and the size in each terminal's own unit instead.
        """
        svg = draw(tmp_path, 'svg')
        sizes = {float(s) * PX for s in re.findall(r'font-size="([\d.]+)"', svg.read_text())}
        assert sizes == {6.0}, f'the web type is {sizes} points, the printed type is 6'

    def test_the_plot_area_agrees_between_the_two(self, tmp_path):
        """
        The real question, and the one a font or a unit mistake shows up in: the axes have to
        land in the same place on both canvases. 5 % of the canvas, because the terminals
        measure text slightly differently and will never agree exactly -- a mis-set font moved
        this by 30 %.
        """
        for kind in ('pdf', 'svg'):
            (tmp_path / kind).mkdir()
        pdf, svg = draw(tmp_path / 'pdf', 'pdf'), draw(tmp_path / 'svg', 'svg')

        drawn = re.search(rb'([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) re', _content(pdf))
        assert drawn, 'no plot frame in the PDF'
        printed = float(drawn.group(3))
        web = _frame_width(svg) * PX

        assert abs(web - printed) / 288.0 < 0.05, \
            f'the plot area is {printed:.1f}pt in print and {web:.1f}pt on the web'


def _content(pdf: pathlib.Path) -> bytes:
    """Every decompressed content stream of a PDF, concatenated."""
    raw, out = pdf.read_bytes(), b''
    for match in re.finditer(rb'stream\r?\n', raw):
        chunk = raw[match.end():raw.find(b'endstream', match.end())]
        try:
            out += zlib.decompress(chunk)
        except zlib.error:
            continue
    return out


def _frame_width(svg: pathlib.Path) -> float:
    """
    The width of the plot frame, which gnuplot's `svg` terminal closes with a `Z` where
    `pdfcairo` writes a `re`. Taken as the widest closed path that is not the whole canvas.
    """
    widths = []
    for path in re.findall(r"d='(M[^']*Z)", svg.read_text()):
        xs = [float(x) for x, _ in re.findall(r'([\d.]+),([\d.]+)', path)]
        if xs:
            widths.append(max(xs) - min(xs))
    assert widths, 'no closed path in the SVG'
    return max(widths)
