import pytest
import tempfile
import sys

from core.convertor import Convertor


@pytest.fixture
def simple_file():
    yield infile, outfile
    infile.close()
    outfile.close()


class TestQuotes():
    def test_convert(self):
        infile = tempfile.SpooledTemporaryFile(mode='w+')
        outfile = tempfile.SpooledTemporaryFile(mode='r')
        infile.write('PENIS')
        Convertor('latex', 'sk', infile, outfile).run()

        print(infile, outfile)
        outfile.seek(0)
        print(outfile.read())
        outfile.seek(0)
        assert outfile.read() == 'Vieme, že "dačo"'
