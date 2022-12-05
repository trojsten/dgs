import pytest
import re
import tempfile
import sys

from core.builder.convertor import Convertor


@pytest.fixture
def convert():
    def _convert(format, language, string):
        infile = tempfile.SpooledTemporaryFile(mode='w+')
        outfile = tempfile.SpooledTemporaryFile(mode='w+')
        infile.write(string)
        infile.seek(0)
        Convertor(format, language, infile, outfile).run()
        outfile.seek(0)
        return outfile.read()

    return _convert

@pytest.fixture
def convert_latexsk(convert):
    def _convert(string):
        return convert('latex', 'sk', string)

    return _convert


class TestQuotes():
    def test_math_plus(self, convert):
        assert convert('latex', 'sk', '"+"') == r'„+“' + '\n'

    def test_more_math(self, convert):
        output = convert('latex', 'sk', r'"$\left(+1, +5\right)$"')
        assert output == r'„\(\left(+1, +5\right)\)“' + '\n'

    def test_slovak(self, convert):
        output = convert('latex', 'sk', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert output == r'Máme „dačo“ a „niečo“. „Čo také?“ \emph{„Asi nič.“}' + '\n'

    def test_slovak_html(self, convert):
        output = convert('html', 'sk', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert output == r'<p>Máme „dačo“ a „niečo“. „Čo také?“ <em>„Asi nič.“</em></p>' + '\n'

    def test_interpunction(self, convert):
        output = convert('latex', 'sk', '"Toto je veľká 0." "Joj?" "???" "!!!"')
        assert output == r'„Toto je veľká 0.“ „Joj?“ „???“ „!!!“' + '\n'

    def test_more_interpunction(self, convert):
        assert convert('latex', 'sk', 'Ale "to" je "dobré", "nie."?') == r'Ale „to“ je „dobré“, „nie.“?' + '\n'

    def test_english_interpunction(self, convert):
        assert convert('latex', 'en', 'Ale "to" je "dobré", "nie."?') == r'Ale “to” je “dobré”, “nie.”?' + '\n'

    def test_french_interpunction(self, convert):
        assert convert('latex', 'fr', 'Ale "to" je "dobré", "nie."?') == r'Ale «\,to\,» je «\,dobré\,», «\,nie.\,»?' + '\n'

    def test_spanish_interpunction(self, convert):
        assert convert('latex', 'es', 'Ale "to" je "dobré", "nie."?') == r'Ale «to» je «dobré», «nie.»?' + '\n'

    def test_english(self, convert):
        output = convert('latex', 'en', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert output == r'Máme “dačo” a “niečo”. “Čo také?” \emph{“Asi nič.”}' + '\n'


class TestImages():
    def test_image_latex(self, convert):
        output = convert('latex', 'sk', '![Masívna ryba](ryba.svg){#fig:ryba height=47mm}')
        assert r'\insertPicture[width=\textwidth,height=47mm]{ryba.pdf}' in output

    def test_image_html(self, convert):
        output = convert('html', 'sk', '![Masívna ryba](ryba.svg){#fig:ryba height=47mm}')
        assert re.match(r'<figure>.*<img.*src=".*ryba.svg".*Masívna ryba.*<figcaption.*Masívna ryba.*</figcaption>.*</figure>', output, flags=re.DOTALL) is not None


class TestTags():
    def test_h_latex(self, convert):
        output = convert('latex', 'en', '@H this should not be seen!')
        assert output == '\n'

    def test_h_html(self, convert):
        output = convert('html', 'en', '@H this should not be seen!')
        assert 'this should not be seen' in output

    def test_l_latex(self, convert):
        output = convert('latex', 'en', '@L this should not be seen!')
        assert 'this should not be seen' in output

    def test_l_html(self, convert):
        output = convert('html', 'en', '@L this should not be seen!')
        assert output == '\n'

    def test_e_latex(self, convert):
        output = convert('latex', 'sk', '@E error')
        assert re.match(r'\\errorMessage\{error\}\n', output) is not None

    def test_e_html(self, convert):
        output = convert('html', 'sk', '@E error')
        assert re.match(r'<p>Error: error</p>', output) is not None

    def test_aligned(self, convert):
        output = convert('latex', 'sk', '$${\na\n}$$')
        assert re.match(r'\\\[.*\\begin\{aligned\}\na\n\\end\{aligned\}.*\\\]', output, flags=re.DOTALL) is not None
