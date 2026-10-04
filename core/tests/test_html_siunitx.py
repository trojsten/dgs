r"""
siunitx, rewritten for the web.

MathJax has no siunitx extension -- none exists -- and the sources make some 9200 siunitx calls
inside maths, so `core/filters/siunitx.lua` rewrites them into plain LaTeX before the page is
written. These tests hold that rewriting to the only authority there is: **what siunitx itself
prints under `core/latex/siunitx.tex`**.

Every expectation below was read off a compiled PDF, not reasoned out. That matters more than
usual here, because the settings are not guessable: `inter-unit-product={}` really does print
`J/(kgK)` with no space between the two denominator units, and `\num{e-4}` really does print as
`10^{-4}` with no mantissa at all.
"""
import tempfile

import pytest

from core.builder.convertor import Convertor
from core.html import siunitx


def convert(markdown: str) -> str:
    """Through the real convertor, so the test exercises the filter the build uses."""
    with tempfile.NamedTemporaryFile('w+', suffix='.md') as infile, \
         tempfile.NamedTemporaryFile('w+', suffix='.html') as outfile:
        infile.write(markdown)
        infile.seek(0)
        return Convertor('html', 'sk', infile, outfile).run()


class TestTheTableComesFromTheLaTeX:
    """
    The unit vocabulary is generated, not transcribed, so that a `\\DeclareSIUnit` added to
    `core/latex/siunitx.tex` tomorrow reaches the web without anyone remembering this module.
    """

    def test_the_generated_table_is_current(self):
        """The `--check` shape `core/audit/macros.py` and `core/builder/reference.py` both use."""
        assert siunitx.TABLE_LUA.read_text() == siunitx.generate(), \
            "core/filters/siunitx-table.lua is stale: run `python -m core.html.siunitx`"

    def test_every_declared_unit_is_in_the_table(self):
        """Both directions: the table may not invent a unit either."""
        declared = siunitx.custom_units()
        assert declared, "no \\DeclareSIUnit found -- has siunitx.tex moved?"
        table = siunitx.TABLE_LUA.read_text()
        for name in declared:
            assert f'["{name}"]' in table, f'\\{name} is declared in siunitx.tex and not in the table'

    def test_a_unit_the_corpus_writes_is_known(self):
        """`\\litre` is written 305 times; a table that lost it would be found by a reader, late."""
        units = dict(siunitx.UNITS) | siunitx.custom_units()
        for name in ('metre', 'second', 'litre', 'celsius', 'eur', 'gforce', 'parsec'):
            assert name in units


class TestAgainstCompiledSiunitx:
    """Each expectation is what `pdflatex` prints with `core/latex/siunitx.tex` loaded."""

    @pytest.mark.parametrize('source, expected', [
        # `3 m/s` -- `per-mode=symbol`, and a thin space between number and unit
        (r'$\qty{3}{\metre\per\second}$', r'3\,\mathrm{m}/\mathrm{s}'),
        # `4180 J/(kgK)` -- two units in the denominator are bracketed, and `inter-unit-product`
        # is empty, so there is no space between them. This is the one everybody guesses wrong.
        (r'$\qty{4180}{\joule\per\kilo\gram\per\kelvin}$',
         r'4180\,\mathrm{J}/\left(\mathrm{kg}\mathrm{K}\right)'),
        # `10 690` -- grouped from five digits up
        (r'$\num{10690}$', r'10\,690'),
        # `1000` -- and not below
        (r'$\num{1000}$', r'1000'),
        # `10^{-4}` -- a bare exponent prints no mantissa
        (r'$\num{e-4}$', r'10^{-4}'),
        # `1.8 · 10^{-4}` -- `exponent-product` is \cdot, not \times
        (r'$\num{1.8e-4}$', r'1.8\cdot10^{-4}'),
        (r'$\ang{45}$', r'45^\circ'),
        (r'$\qty{20}{\celsius}$', r'20\,^\circ\mathrm{C}'),
        (r'$\qty{5}{\metre\squared}$', r'5\,\mathrm{m}^{2}'),
        # the unit is repeated on both ends by `range-units`
        (r'$\qtyrange{75}{77}{\centi\metre}$',
         '75\\,\\mathrm{cm}\\text{ – }77\\,\\mathrm{cm}'),
    ])
    def test_it_prints_what_siunitx_prints(self, source, expected):
        assert expected in convert(source)

    def test_per_mode_reciprocal_is_honoured_per_call(self):
        """145 call sites choose `per-mode` themselves; the default is `symbol`."""
        assert r'\mathrm{rad}\mathrm{s}^{-1}' in convert(
            r'$\qty[per-mode=reciprocal]{23}{\radian\per\second}$')

    def test_parse_numbers_false_passes_the_value_through(self):
        """~190 call sites write a TeX expression where a number would go."""
        assert r'\pi\,\mathrm{mm}^{2}' in convert(
            r'$\qty[parse-numbers=false]{\pi}{\milli\metre\squared}$')

    def test_a_custom_unit_declared_in_the_latex(self):
        assert r'\text{€}' in convert(r'$\qty{5}{\eur}$')


class TestItStaysOutOfEverythingElse:
    """
    The half that carries the argument for doing this in the AST rather than over the text.

    Pandoc has already decided what is maths. A `\\qty` in a code block, in a URL or in an image
    path is a different node type, and a filter written over `Math` cannot reach it -- which a
    regex bank running before pandoc would have to re-detect, one line at a time.
    """

    def test_a_qty_in_a_code_block_is_left_alone(self):
        html = convert('```\n\\qty{3}{\\metre\\per\\second}\n```\n')
        assert r'\qty{3}{\metre\per\second}' in html

    def test_a_qty_in_inline_code_is_left_alone(self):
        assert r'\qty{3}{\metre}' in convert('text `\\qty{3}{\\metre}` more\n')

    def test_prose_that_merely_looks_like_a_unit_is_left_alone(self):
        """`\\per` outside maths is not siunitx's and is not ours to touch."""
        html = convert('A sentence mentioning litre and metre and second.\n')
        assert 'litre and metre and second' in html


class TestAnUnknownUnitIsRefused:
    """
    A unit with no symbol must stop the build by name. The alternative is a page that prints the
    macro, or silently prints nothing, which is how a wrong unit reaches a reader.
    """

    def test_it_names_the_unit(self):
        with pytest.raises(Exception, match=r'furlong'):
            convert(r'$\qty{3}{\furlong}$')
