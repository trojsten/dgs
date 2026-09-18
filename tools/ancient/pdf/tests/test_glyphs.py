r"""
Reading the glyph stream out of one page of a booklet.
"""

from tools.ancient.pdf.glyphs import _numbers

PAGE = """\
<page mediabox="0 0 595 842">
<fill_text transform="1 0 0 -1 0 842">
    <span font="ABCDEF+cmr120462" wmode="0" bidi="0" trm="12 0 0 12">
        <g unicode="?" glyph="G46" x="100" y="700" adv=".5"/>
        <g unicode="?" glyph="G46._" x="110" y="700" adv=".5"/>
        <g unicode="?" glyph="one" x="120" y="700" adv=".5"/>
    </span>
</fill_text>
</page>
"""


class TestDuplicateGlyphNames:
    def test_a_plain_name_is_its_number(self):
        assert _numbers(PAGE)[0][1] == 46

    def test_the_second_glyph_of_the_same_name_is_numbered_apart(self):
        # `04.pdf`'s `cmr` charset holds two glyphs both called `G46`, and mupdf suffixes the
        # second. Unmatched it decoded to nothing and was dropped in silence: `\qty{75}{\percent}`
        # printed as `\qty{5}{\percent}` and `v = 400/27` as `v = 400/2`, because that glyph
        # is the digit 7.
        assert _numbers(PAGE)[1][1] == -46

    def test_a_real_name_still_has_no_number(self):
        # `10.pdf` and `11.pdf` name their glyphs properly and decode by unicode instead.
        assert _numbers(PAGE)[2][1] is None
