r"""
`core/latex/math.tex` on the web.

The macros are expanded to plain LaTeX before the page is written rather than configured into
MathJax, because most of them cannot be said in a MathJax macro table: `\FDiff` is declared
`e{^_} t[ m`, an xparse embellishment that takes `^` and `_` groups in either order, and it is
written 951 times; `\Int` takes two leading optionals; `\Coord` splits a list at the TeX level.
MathJax expresses one leading optional argument and nothing else.

The expectations here are what `pdflatex` prints with `math.tex` loaded, not what seemed
reasonable -- the same bargain as `test_html_siunitx.py`.
"""
import tempfile

import pytest

from core.builder.convertor import Convertor
from core.html import macros


def convert(markdown: str) -> str:
    with tempfile.NamedTemporaryFile('w+', suffix='.md') as infile, \
         tempfile.NamedTemporaryFile('w+', suffix='.html') as outfile:
        infile.write(markdown)
        infile.seek(0)
        return Convertor('html', 'sk', infile, outfile).run()


class TestEveryMacroTheSourcesUseIsCovered:
    """
    The half that keeps this from rotting. A macro written in a source and missing from the
    table reaches the page as itself -- a backslash and a word -- and nothing else would say so.
    """

    def test_nothing_written_is_uncovered(self):
        missing = sorted(macros.used() - set(macros.MACROS))
        assert not missing, \
            f'written in the sources and not in the table: {" ".join(missing)}'

    def test_the_generated_table_is_current(self):
        assert macros.TABLE_LUA.read_text() == macros.generate(), \
            'core/filters/macros-table.lua is stale: run `python -m core.html.macros`'

    def test_the_table_invents_nothing(self):
        """Every entry must name a macro `math.tex` or `symbols.tex` actually defines."""
        invented = sorted(set(macros.MACROS) - macros.defined())
        assert not invented, f'in the table and defined nowhere: {" ".join(invented)}'


class TestAgainstCompiledLaTeX:
    """Each expectation was read off a PDF compiled with `core/latex/math.tex` loaded."""

    @pytest.mark.parametrize('source, expected', [
        # `(x + y)` -- \DeclarePairedDelimiter, starred, which is \left…\right
        (r'$\Paren{x + y}$', r'\left(x + y\right)'),
        # `|v|` -- and a space, or `\lvert` runs into the `v` and becomes a control word
        (r'$\Abs{v}$', r'\left\lvert v\right\rvert'),
        # `∆H`
        (r'$\FDiff{H}$', r'\mathrm{\Delta} H'),
        (r'$\Int[0][1]{x^2}{x}$', r'\int\limits_{0}^{1} x^2\,\mathrm{d}x'),
        (r'$\Sum[i=1][n]{a_i}$', r'\sum\limits_{i=1}^{n} a_i'),
        (r'$\Coord{3; 4}$', r'\left[3; 4\right]'),
        (r'$a \Implies b$', r'a \quad\Rightarrow\quad b'),
        (r'$\QText{a tak}$', r'\quad\text{a tak}\quad'),
        (r'$\Earth$', r'\oplus'),
        (r'$\Mean{x}$', r'\overline{x}'),
    ])
    def test_it_prints_what_math_tex_prints(self, source, expected):
        assert expected in convert(source)

    @pytest.mark.parametrize('source', [r'$\FDiff^2_x{H}$', r'$\FDiff_x^2{H}$'])
    def test_the_embellishment_takes_either_order(self, source):
        """
        `e{^_}` collects the two groups whichever way round they are written, and 1504 call
        sites depend on it. Both spellings are in the corpus.
        """
        assert r'\mathrm{\Delta}^{2}_{x} H' in convert(source)

    def test_an_embellishment_may_be_absent(self):
        assert r'\mathrm{\Delta} H' in convert(r'$\FDiff{H}$')


class TestItStaysOutOfEverythingElse:
    """A macro in a code block is not maths and is not this filter's to expand."""

    def test_a_macro_in_a_code_block_is_left_alone(self):
        assert r'\Paren{x}' in convert('```\n\\Paren{x}\n```\n')

    def test_a_word_that_looks_like_a_macro_in_prose(self):
        assert 'Paren' in convert('The word Paren in prose.\n')
