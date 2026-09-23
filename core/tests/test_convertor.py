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
        # `s\u00a0newlinami`: the caption is prose, so `core/filters/spacing.lua` glues the
        # Slovak preposition in it like anywhere else.
        assert re.match(r'.*<figcaption.*Veľmi dlhý text\. Akože masívne\. Veľmi masívne\. Aj s\u00a0newlinami\.', output) is not None


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


    r"""
    `![](){height=40mm}` is a picture nobody has drawn yet, and must reach `\insertPicture`.

    That macro draws LaTeX's `example-image` for a file that is not there, which is the whole
    point -- a grey panel with a cross through it, plainly missing. The other picture rules
    match on the extension, so without a rule of its own an empty path stays a bare
    `\includegraphics{}` and stops xelatex with ``File `' not found``.
    """

    @staticmethod
    def latex(text):
        from core.builder.convertor import Convertor
        for rule in Convertor.post_regexes['latex']:
            text = rule.pattern.sub(rule.repl, text)
        return text

    def test_an_empty_path_becomes_a_protected_picture(self):
        assert self.latex(r'\includegraphics[height=40mm]{}') == r'\insertPicture[height=40mm]{}'

    def test_it_works_without_options_too(self):
        assert self.latex(r'\includegraphics{}') == r'\insertPicture{}'

    def test_a_real_picture_is_untouched_by_it(self):
        # The quiet case: the extension rules still own everything that has one.
        assert self.latex(r'\includegraphics[height=2cm]{crystal.svg}') == \
            r'\insertPicture[height=2cm]{crystal.pdf}'

    def test_a_path_with_no_extension_is_left_to_fail_loudly(self):
        # A mistyped `![](figure)` is an authoring error and should stop the build, not quietly
        # render as a placeholder.
        assert self.latex(r'\includegraphics{figure}') == r'\includegraphics{figure}'


class TestSpacing:
    r"""
    `core/filters/spacing.lua` inserts the non-breaking spaces the language wants.

    Half of these tests are cases that must stay quiet. They are the ones that matter: a pass
    that glues text is only safe because the pandoc AST has already separated prose from maths,
    code, image targets and raw TeX, and the way to keep that true is to pin it.
    """

    def test_preposition_is_glued(self, convert):
        assert convert('latex', 'sk', 'Teleso v tiaži') == 'Teleso v~tiaži'

    def test_every_one_letter_word_is_glued(self, convert):
        assert convert('latex', 'sk', 'V zime a v lete') == 'V~zime a~v~lete'

    def test_glues_to_maths(self, convert):
        assert convert('latex', 'sk', 'hmotnosť v $x$') == r'hmotnosť v~\(x\)'

    def test_glues_to_raw_tex(self, convert):
        assert convert('latex', 'sk', r'v \qty{5}{\kilo\gram}') == r'v~\qty{5}{\kilo\gram}'

    def test_glues_across_a_source_line_break(self, convert):
        """`--wrap=preserve` keeps the newline, and TeX reads a newline as a breakable space."""
        assert convert('latex', 'sk', 'teleso a\ntabuľku') == 'teleso a~tabuľku'

    def test_opening_bracket_does_not_hide_the_preposition(self, convert):
        assert convert('latex', 'sk', '(v tiaži)') == '(v~tiaži)'

    def test_html_gets_the_character_itself(self, convert):
        assert convert('html', 'sk', 'v tiaži') == '<p>v tiaži</p>'

    def test_german_abbreviation_is_narrowed(self, convert):
        """`smart` glues `d. h.` on its own, with a full-width space. Narrow it."""
        assert convert('latex', 'de', 'Wir drehen es, d. h. um $45$ Grad.') == \
            r'Wir drehen es, d.\,h. um \(45\) Grad.'

    def test_german_abbreviation_smart_missed(self, convert):
        """`z. B.` is not on pandoc's list, so it arrives as two words and a `Space`."""
        assert convert('latex', 'de', 'Wir nehmen z. B. Wasser.') == r'Wir nehmen z.\,B. Wasser.'

    def test_slovak_abbreviation_takes_a_full_width_space(self, convert):
        assert convert('latex', 'sk', 'Je to t. j. asi toľko.') == 'Je to t.~j. asi toľko.'

    # ------------------------------------------------------------------ must stay quiet

    def test_english_is_left_alone(self, convert):
        """English declares no `typography:`, and must not inherit anyone else's."""
        assert convert('latex', 'en', 'a cat in a hat') == 'a cat in a hat'

    def test_german_gets_no_prepositions(self, convert):
        assert convert('latex', 'de', 'Ich v z k o') == 'Ich v z k o'

    def test_a_hand_written_space_is_not_doubled(self, convert):
        """The author's `\\ ` is already U+00A0 inside the `Str`: there is no `Space` left."""
        assert convert('latex', 'sk', r'v\ tiaži') == 'v~tiaži'
        assert convert('latex', 'sk', r'v\ tiaži').count('~') == 1

    def test_maths_is_untouched(self, convert):
        assert convert('latex', 'sk', '$v = a$') == r'\(v = a\)'

    def test_code_is_untouched(self, convert):
        assert convert('latex', 'sk', '`v tiaži`') == r'\texttt{v\ tiaži}'

    def test_an_image_path_is_untouched(self, convert):
        assert 'v a.png' in convert('latex', 'sk', '![x](v a.png){height=10mm}')

    def test_an_abbreviation_is_not_a_preposition(self, convert):
        """`z.` ends in a period, so Slovak's `z` rule must not fire on it."""
        assert convert('latex', 'sk', 'Je to z. B. asi toľko.') == 'Je to z. B. asi toľko.'

    def test_thinspace_written_by_hand_still_works(self, convert):
        """The escape hatch for a pair the table does not know."""
        assert convert('latex', 'de', r'Wir nehmen d.\thinspace h. Wasser.') == \
            r'Wir nehmen d.\thinspace h. Wasser.'

    # ------------------------------------------------------------------ the rule table

    @staticmethod
    def _convertor(language):
        infile = tempfile.NamedTemporaryFile(mode='w+')
        outfile = tempfile.NamedTemporaryFile(mode='w+')
        return Convertor('latex', language, infile, outfile)

    def test_both_cases_are_derived(self):
        """A single is listed once in the YAML; the capital comes from here, not from Lua."""
        assert set('vVzZ') <= set(self._convertor('sk').nbsp_singles)

    def test_cyrillic_case_is_derived_too(self):
        """Lua's `string.lower` is byte-oriented, so the casing has to happen in Python."""
        assert {'в', 'В'} <= set(self._convertor('ru').nbsp_singles)

    def test_two_letter_words_get_their_title_case(self):
        """
        Ukrainian's list holds two-letter prepositions, and a sentence opens with `Із`, not `ІЗ`.

        For a one-letter word `upper()` and `capitalize()` agree, which is why deriving only the
        upper form went unnoticed until the two-letter forms were added.
        """
        singles = set(self._convertor('uk').nbsp_singles)
        assert {'із', 'ІЗ', 'Із'} <= singles

    def test_a_two_letter_preposition_is_glued(self, convert):
        assert convert('latex', 'uk', 'Із цього та з того') == 'Із~цього та з~того'

    def test_a_language_without_rules_gets_none(self):
        english = self._convertor('en')
        assert english.nbsp_singles == []
        assert english.nbsp_pairs == []
        assert english.thin_pairs == []

    def test_default_yaml_carries_no_typography(self):
        """
        Same reason `default.yaml` carries no `words:`: `merge()` would make whatever it held the
        fallback for every language, and English inheriting Slovak's prepositions is the failure
        this exists to end.
        """
        import yaml
        with open('core/i18n/default.yaml') as f:
            assert 'typography' not in yaml.safe_load(f)


class TestCrossrefLabelSurvives:
    r"""
    A label that pandoc did not read as an attribute is typeset as text, and refused here.

    Pandoc accepts `{#eq:…}` only when whitespace or the end of the block follows it. Glue a word
    to it and the attribute degrades to literal `\{\#eq:…\}`: the equation loses its number, its
    `\label`, and every `[-@eq:…]` that points at it. `22/hop/hu` printed `{#eq:hop:vxvvxgd}` into
    the Hungarian booklet that way.

    `settle_display_tags` stops the renderer from producing one. This is the net under a block
    somebody wrote by hand, which no check upstream can see, and it refuses the page rather than
    printing the label.
    """

    BLOCK = 'lead\n$$\n    a = b.\n$$ {#eq:x:y}'

    def test_a_good_label_passes(self, convert):
        assert '\\label{eq:x:y}' in convert('latex', 'sk', self.BLOCK + '\n')

    def test_a_label_with_a_word_glued_to_it_is_refused(self, convert):
        with pytest.raises(Exception, match='typeset as text'):
            convert('latex', 'sk', self.BLOCK + 'trail\n')

    def test_a_label_followed_by_a_space_is_fine(self, convert):
        """The space is the whole difference -- do not refuse the form that works."""
        assert '\\label{eq:x:y}' in convert('latex', 'sk', self.BLOCK + ' trail\n')
