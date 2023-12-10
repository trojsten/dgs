import pytest
import re
import tempfile

from core.builder.convertor import Convertor


@pytest.fixture
def convert():
    def _convert(fmt, language, string):
        infile = tempfile.NamedTemporaryFile(mode='w+')
        outfile = tempfile.NamedTemporaryFile(mode='w+')
        infile.write(string)
        infile.seek(0)
        Convertor(fmt, language, infile, outfile).run()
        outfile.seek(0)
        return outfile.read()

    return _convert


class DisabledTestQuotes:
    """ These tests are currently disabled: we have switched to `csquotes` """
    def test_math_plus(self, convert):
        assert convert('latex', 'sk', '"+"') == r'„+“' + '\n'

    def test_more_math(self, convert):
        output = convert('latex', 'sk', r'"$\left(+1, +5\right)$"')
        assert output == r'„\(\left(+1, +5\right)\)“' + '\n'

    def test_slovak(self, convert):
        output = convert('latex', 'sk', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert output.replace("{}", "") == r'Máme „dačo“ a „niečo“. „Čo také?“ \emph{„Asi nič.“}' + '\n'

    def test_slovak_html(self, convert):
        output = convert('html', 'sk', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert output == r'<p>Máme „dačo“ a „niečo“. „Čo také?“ <em>„Asi nič.“</em></p>' + '\n'

    def test_interpunction(self, convert):
        output = convert('latex', 'sk', '"Toto je veľká 0." "Joj?" "???" "!!!"')
        assert output.replace("{}", "") == r'„Toto je veľká 0.“ „Joj?“ „???“ „!!!“' + '\n'

    def test_more_interpunction(self, convert):
        assert convert('latex', 'sk', 'Ale "to" je "dobré", "nie."?') == r'Ale „to“ je „dobré“, „nie.“?' + '\n'

    def test_english_interpunction(self, convert):
        assert convert('latex', 'en', 'Ale "to" je "dobré", "nie."?') == r'Ale “to” je “dobré”, “nie.”?' + '\n'

    def test_french_interpunction(self, convert):
        assert (convert('latex', 'fr', 'Ale "to" je "dobré", "nie."?') ==
                r'Ale «\,to\,» je «\,dobré\,», «\,nie.\,»?' + '\n')

    def test_spanish_interpunction(self, convert):
        assert convert('latex', 'es', 'Ale "to" je "dobré", "nie."?') == r'Ale «to» je «dobré», «nie.»?' + '\n'

    def test_english(self, convert):
        output = convert('latex', 'en', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert output == r'Máme “dačo” a “niečo”. “Čo také?” \emph{“Asi nič.”}' + '\n'


class TestImages:
    def test_image_latex(self, convert):
        output = convert('latex', 'sk', '![Masívna ryba](ryba.svg){#fig:ryba height=47mm}')
        assert r'\insertPicture[width=\textwidth,height=47mm]{ryba.pdf}' in output

    def test_image_latex_multiline(self, convert):
        output = convert('latex', 'sk', """
![Veľmi dlhý text. Akože masívne.
Veľmi masívne.
Aj s newlinami.](subor.png){#fig:dlhy height=53mm}
""")
        assert re.search(r'\\insertPicture\[width=\\textwidth,height=53mm]{subor\.png}', output) is not None

    def test_image_html(self, convert):
        output = convert('html', 'sk', '![Masívna ryba](ryba.svg){#fig:ryba height=47mm}')
        assert re.match(r'<figure>.*<img.*src=".*ryba.svg".*<figcaption.*Masívna ryba.*</figcaption>.*</figure>',
                        output, flags=re.DOTALL) is not None

    def test_image_html_multiline(self, convert):
        output = convert('html', 'sk', """
![Veľmi dlhý text. Akože masívne.
Veľmi masívne.
Aj s newlinami.](subor.png){#fig:dlhy height=53mm}
""")
        output = output.replace('\n', ' ')
        assert re.match(r'<figure>.*<img.* src=".*subor\.png".*<figcaption.*Veľmi dlhý text\. Akože masívne\. '
                        r'Veľmi masívne\. Aj s newlinami\..*</figcaption>.*</figure>', output) is not None


class TestTags:
    def test_h_latex(self, convert):
        output = convert('latex', 'en', '@H this should not be seen!')
        assert output == '\n'

    def test_h_html(self, convert):
        output = convert('html', 'en', '@H this should not be seen!')
        assert output == '<p>this should not be seen!</p>\n'

    def test_l_latex(self, convert):
        output = convert('latex', 'en', '@L this should not be seen!')
        assert output == 'this should not be seen!\n'

    def test_l_html(self, convert):
        output = convert('html', 'en', '@L this should not be seen!')
        assert output == '\n'

    def test_e_latex(self, convert):
        output = convert('latex', 'sk', '@E error')
        assert re.match(r'\\errorMessage\{error}\n', output) is not None

    def test_e_html(self, convert):
        output = convert('html', 'sk', '@E error')
        assert re.match(r'<p>Error: error</p>', output) is not None

    def test_aligned(self, convert):
        output = convert('latex', 'sk', '$${\na\n}$$')
        assert re.match(r'\\\[.*\\begin\{aligned}\na\n\\end\{aligned}.*\\]', output, flags=re.DOTALL) is not None
