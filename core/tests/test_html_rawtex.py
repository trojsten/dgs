r"""
LaTeX written in prose, which the HTML writer throws away without a word.

siunitx and mhchem work outside maths and the sources use that -- `\qty{0.900}{\percent}` and
`\ce{NaCl}` are written in running text 550 times across phys and chem. The LaTeX writer passes
each through; the HTML writer drops it and says nothing, so `chem/01/robinson` asked its reader
for "jeden ekvivalent ." with the reagent gone.
"""
import tempfile

import pytest

from core.builder.convertor import Convertor


def convert(markdown: str) -> str:
    """Through the real convertor, so the test exercises the filter the build uses."""
    with tempfile.NamedTemporaryFile('w+', suffix='.md') as infile, \
         tempfile.NamedTemporaryFile('w+', suffix='.html') as outfile:
        infile.write(markdown)
        infile.seek(0)
        return Convertor('html', 'sk', infile, outfile).run()


class TestItFires:
    """Raw TeX in prose reaches the page as maths, whichever engine then sets it."""

    @pytest.mark.parametrize('source, fragment', [
        (r'Pridaný jeden ekvivalent \ce{MeLi}.', r'\ce{MeLi}'),
        (r'Roztok \qty{0.900}{\percent}.', r'\qty{0.900}{\percent}'),
        (r'Uhol \ang{32.53} od zvislice.', r'\ang{32.53}'),
        (r'Vzorec \ce{C21H28O2}?', r'\ce{C21H28O2}'),
    ])
    def test_it_becomes_maths(self, source, fragment):
        out = convert(source)
        assert 'class="math inline"' in out
        assert fragment in out

    def test_the_sentence_keeps_its_punctuation(self):
        """The defect was a full stop with nothing in front of it; the fix must not move it."""
        out = convert(r'Pridaný jeden ekvivalent \ce{MeLi}.')
        assert '</span>.' in out


class TestItStaysQuiet:
    """Three things that look like the case above and are not."""

    def test_a_print_only_macro_is_dropped_rather_than_set(self):
        r"""`\vspace` is a page instruction. A page that reflows has nowhere to put it."""
        out = convert('Prvý odsek.\n\n\\vspace{3mm}\n\nDruhý odsek.')
        assert 'vspace' not in out
        assert 'Prvý odsek' in out and 'Druhý odsek' in out

    def test_maths_already_in_dollars_is_not_touched(self):
        """It is a `Math` node already; wrapping it again would nest the delimiters."""
        out = convert(r'Soľ $\ce{NaCl}$ sa rozpustí.')
        assert out.count('class="math inline"') == 1
        assert r'\(\ce{NaCl}\)' in out

    def test_a_macro_inside_code_is_left_as_code(self):
        """`Code` is its own node type, so the filter cannot reach it -- and must not."""
        out = convert('Napíš `\\qty{1}{\\metre}` do zdroja.')
        assert '<code>' in out
        assert 'class="math' not in out
