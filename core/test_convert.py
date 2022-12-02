import pytest
import tempfile
import sys

from core.convertor import Convertor


@pytest.fixture
def convert():
    def _convert(format, language, string):
        infile = tempfile.SpooledTemporaryFile(mode='w+')
        outfile = tempfile.SpooledTemporaryFile(mode='w+')
        infile.write(string)
        infile.seek(0)
        Convertor(format, language, infile, outfile).run()
        outfile.seek(0)
        return outfile

    return _convert

@pytest.fixture
def convert_latexsk(convert):
    def _convert(string):
        return convert('latex', 'sk', string)

    return _convert


class TestQuotes():
    def test_math(self, convert_latexsk):
        assert convert_latexsk('"+"').read() == r'„+“' + '\n'

    def test_more_math(self, convert_latexsk):
        assert convert_latexsk(r'"$\left(+1, +5\right)$"').read() == r'„\(\left(+1, +5\right)\)“' + '\n'

    def test_slovak(self, convert):
        outfile = convert('latex', 'sk', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert outfile.read() == r'Máme „dačo“ a „niečo“. „Čo také?“ \emph{„Asi nič.“}' + '\n'

    def test_interpunction(self, convert_latexsk):
        assert convert_latexsk('"Toto je veľká 0" "..." "???" "!!!"').read() == r'„Toto je veľká 0“ „\ldots{}“ „???“ „!!!“' + '\n'

    def test_english(self, convert):
        outfile = convert('latex', 'en', 'Máme "dačo" a "niečo". "Čo také?" _"Asi nič."_')
        assert outfile.read() == r'Máme “dačo” a “niečo”. “Čo také?” \emph{“Asi nič.”}' + '\n'
