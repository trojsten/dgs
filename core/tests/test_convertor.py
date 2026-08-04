import re
import tempfile

import pytest

from core.builder.convertor import Convertor


@pytest.fixture
def convert():
    def _convert(fmt, language, string):
        infile = tempfile.NamedTemporaryFile(mode='w+')
        outfile = tempfile.NamedTemporaryFile(mode='w+')
        infile.write(string)
        infile.seek(0)
        outfile.write(Convertor(fmt, language, infile, outfile).run())
        outfile.seek(0)
        return outfile.read()

    return _convert


@pytest.mark.skip(reason="We have switched to \\enquote for LaTeX, HTML port underway")
class TestQuotes:
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
        output = output.replace('\n', ' ')
        assert re.search(r'\\insertPicture\[width=\\linewidth,height=47mm,keepaspectratio]{.*}', output) is not None, \
            f"Got '{output}'"
        assert 'ryba.pdf' in output

    def test_image_latex_multiline(self, convert):
        output = convert('latex', 'sk', """
![Veľmi dlhý text. Akože masívne.
Veľmi masívne.
Aj s newlinami.](file.png){#fig:long height=53mm}
""")
        output = output.replace('\n', ' ')
        # A captioned raster image also picks up pandoc's `alt` key (SVGs do not).
        assert re.search(r'\\insertPicture\[width=\\linewidth,height=53mm,keepaspectratio,alt=\{[^}]*}]{.*}',
                         output) is not None, f"Got '{output}'"
        assert 'file.png' in output

    def test_image_without_attributes_is_refused(self, convert):
        """
        Pandoc wraps an attribute-less image in `\\pandocbounded`, a macro that lives in
        pandoc's own template. DGS emits fragments, so it would be undefined at compile
        time -- the convertor must refuse instead.
        """
        with pytest.raises(Exception, match='pandocbounded'):
            convert('latex', 'sk', '![Masívna ryba](ryba.svg)')

    def test_image_html(self, convert):
        output = convert('html', 'sk', '![Masívna ryba](ryba.svg){#fig:ryba height=47mm}')
        output = output.replace('\n', ' ')
        assert re.match(r'<figure.*>.*</figure>', output) is not None
        assert re.match(r'.*<img.* src=".*ryba\.svg"', output) is not None
        assert re.match(r'.*<figcaption.*>.*Masívna ryba.*</figcaption>', output) is not None

    def test_image_html_multiline(self, convert):
        output = convert('html', 'sk', """
![Veľmi dlhý text. Akože masívne.
Veľmi masívne.
Aj s newlinami.](file.png){#fig:long height=53mm}
""")
        output = output.replace('\n', ' ')
        assert re.match(r'<figure.*>.*</figure>', output) is not None
        assert re.match(r'.*<img.* src=".*file\.png".* />', output) is not None
        assert re.match(r'.*<figcaption.*Veľmi dlhý text\. Akože masívne\. Veľmi masívne\. Aj s newlinami\.', output) is not None


class TestTags:
    def test_h_latex(self, convert):
        output = convert('latex', 'en', '@H this should not be seen!')
        assert output == '', \
            f"Got '{output}'"

    def test_h_html(self, convert):
        output = convert('html', 'en', '@H this should not be seen!')
        assert output == '<p>this should not be seen!</p>', \
            f"Got '{output}'"

    def test_l_latex(self, convert):
        output = convert('latex', 'en', '@L this should not be seen!')
        assert output == 'this should not be seen!', \
            f"Got '{output}'"

    def test_l_html(self, convert):
        output = convert('html', 'en', '@L this should not be seen!')
        assert output == '', \
            f"Got '{output}'"

    def test_e_latex(self, convert):
        output = convert('latex', 'sk', '@E error')
        assert re.match(r'\\errorMessage\{error}', output) is not None

    def test_e_html(self, convert):
        output = convert('html', 'sk', '@E error')
        assert re.match(r'<p>Error: error</p>', output) is not None

    def test_aligned(self, convert):
        output = convert('latex', 'sk', '$${\na\n}$$')
        assert re.match(r'\\\[.*\\begin\{aligned}\na\n\\end\{aligned}.*\\]', output, flags=re.DOTALL) is not None


class TestLongtableRules:
    r"""
    Pandoc puts a table's `\bottomrule` in `\endlastfoot`, which longtable emits only through
    the output routine when it breaks the table across pages. Inside a box -- the Náboj tearoff
    wraps every problem in fixed-height minipages -- that never happens and the rule silently
    disappears, so it has to be moved into the table body.
    """

    TABLE = "| a | b |\n|:--|:--|\n| 1 | 2 |\n"

    def test_bottom_rule_is_not_left_in_the_foot(self, convert):
        output = convert('latex', 'sk', self.TABLE)
        assert re.search(r'\\bottomrule[^\n]*\n\\endlastfoot', output) is None, f"Got '{output}'"

    def test_bottom_rule_ends_the_table_body(self, convert):
        output = convert('latex', 'sk', self.TABLE)
        assert re.search(r'\\bottomrule\\noalign\{}\n\\end\{longtable}', output) is not None, \
            f"Got '{output}'"

    def test_rule_is_moved_not_duplicated(self, convert):
        assert convert('latex', 'sk', self.TABLE).count(r'\bottomrule') == 1

    def test_html_output_is_untouched(self, convert):
        assert 'bottomrule' not in convert('html', 'sk', self.TABLE)

    def test_unrelated_bottom_rule_stays_put(self):
        """Only the rule immediately preceding \\endlastfoot is relocated."""
        from core.builder.convertor import Convertor
        f = tempfile.SpooledTemporaryFile(mode='w+')
        f.write("row & row \\\\\n\\bottomrule\\noalign{}\n\\end{longtable}\n")
        f.seek(0)
        assert Convertor.move_bottom_rules(f).read() == \
            "row & row \\\\\n\\bottomrule\\noalign{}\n\\end{longtable}\n"

    def test_trailing_rule_at_end_of_file_survives(self):
        """A held rule must still be emitted if the file simply ends."""
        from core.builder.convertor import Convertor
        f = tempfile.SpooledTemporaryFile(mode='w+')
        f.write("text\n\\bottomrule\\noalign{}\n")
        f.seek(0)
        assert Convertor.move_bottom_rules(f).read() == "text\n\\bottomrule\\noalign{}\n"
