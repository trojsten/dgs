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


    def test_tikz_becomes_svg_in_html(self, convert):
        """
        A `.tikz` is LaTeX, so the web gets the SVG the build renders it to -- the same way a
        `.gp` becomes the PNG gnuplot draws. The reference has to follow the picture, or the
        fragment points at a file no browser can load.
        """
        output = convert('html', 'sk', '![Sieť](network.tikz){#fig:net height=40mm}').replace('\n', ' ')
        assert 'network.svg' in output
        assert 'network.tikz' not in output

    def test_gp_becomes_svg_in_html(self, convert):
        """
        A gnuplot plot goes to an SVG, not a PNG, and by the same route a `.tikz` takes.

        It used to go to a PNG built by a second gnuplot run with `-e "set terminal pngcairo"`,
        which never worked once: every `.gp` in the repository opens by setting its own
        `set terminal pdf size W, H`, and that runs after the `-e` and wins. `output/` got a PDF
        carrying a `.png` name, and every browser showed the broken-image icon.
        """
        output = convert('html', 'sk', '![Graf](plot.gp){#fig:plot height=40mm}').replace('\n', ' ')
        assert 'plot.svg' in output
        assert 'plot.gp' not in output

    def test_unconvertible_picture_reference_is_refused(self, convert):
        """
        The backstop behind the two rules above. Both rewrites anchor on `<img src="`, which is
        what pandoc writes -- so what this catches is a reference they did not reach, here an
        `<img>` carrying an attribute before its `src`. A broken `<img>` shows its alt text and
        says nothing about why, so this is the one picture failure that is silent on the page:
        `futile-nine` shipped `src="network.tikz"` and the reader got raw LaTeX instead of nine
        resistors.
        """
        with pytest.raises(Exception, match='no browser can load'):
            convert('html', 'sk', '<img class="figure" src="network.tikz" />')

    def test_a_real_svg_is_left_alone(self, convert):
        """
        The quiet half: `.svg` and `.png` are what a browser wants, so nothing rewrites them and
        the check must not fire on them. `tikz` inside a *name* is not an extension either.
        """
        for picture in ('ryba.svg', 'file.png', 'tikz-sketch.svg', 'a.tikz.svg'):
            output = convert('html', 'sk', f'![Ryba]({picture})' + '{height=40mm}').replace('\n', ' ')
            assert picture in output, f"{picture} was rewritten: {output}"


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


class TestRepeatedHyphen:
    r"""
    Czech, Slovak and Portuguese repeat the hyphen when a word breaks at one.

    `core/filters/hyphens.lua` emits `\rephyphen`, which `core/latex/hacks.tex` defines; see
    there for why the discretionary is built the way it is. The filter is LaTeX-only, because
    there is no Unicode character that repeats a hyphen at a break.
    """

    #: The five languages whose norms require the repetition. See `taste` of each in the locale
    #: file; the sweep that settled the list is recorded in CLAUDE.md.
    REPEATING = ('cs', 'sk', 'pl', 'pt', 'es')

    def test_a_hyphenated_word_gets_the_macro(self, convert):
        for language in self.REPEATING:
            assert r'anti\rephyphen{}inflamatório' in convert('latex', language, 'anti-inflamatório')

    def test_an_enclitic_pronoun_gets_it_too(self, convert):
        """The case Portuguese needs it for: a hyphen inside an ordinary verb."""
        assert r'encontra\rephyphen{}se' in convert('latex', 'pt', 'encontra-se')

    def test_a_language_that_does_not_declare_it_keeps_the_plain_hyphen(self, convert):
        """
        The quiet half. A language that declares nothing gets nothing, which is how every
        `typography:` rule in this project behaves.
        """
        for language in ('en', 'de', 'fr', 'hu', 'ru', 'uk'):
            assert convert('latex', language, 'anti-inflamatório') == 'anti-inflamatório'

    def test_the_macro_is_braced(self, convert):
        r"""Without `{}` the macro runs into the word: `\rephypheninflamatório` is undefined."""
        assert r'\rephyphen{}i' in convert('latex', 'pt', 'anti-inflamatório')

    def test_it_does_not_reach_anything_that_is_not_prose(self, convert):
        """
        The whole argument for doing this in the AST. Hyphens are everywhere in these sources that
        is not prose, and pandoc has already sorted them into node types a `Str` rule cannot see.
        """
        for source in (r'$a-b$', '`x-y`', '2-3',
                       '![](northern-sun.svg){#fig:drag-queen height=40mm}'):
            assert 'rephyphen' not in convert('latex', 'pt', source), source

    def test_a_hyphen_needs_a_letter_on_each_side(self, convert):
        """A dangling hyphen is not a hyphenated word."""
        for source in ('anti- x', 'x -inflamatório'):
            assert 'rephyphen' not in convert('latex', 'pt', source), source

    def test_a_digit_hyphen_is_made_unbreakable(self, convert):
        r"""
        Czech typography forbids dividing `3-dílný` or `10-procentní` at the spojovník, the
        Ukrainian Pravopys forbids separating a grammatical ending from its digits, and the
        Russian rules forbid it for `2-местный` and for multi-digit numbers.

        It has to be said positively rather than by omission: these languages carry a lowered
        `\exhyphenpenalty`, so a hyphen merely *left alone* is freely breakable. Slovak has 70 of
        these in its sources -- `10-stupňovej`, `12-krát`, `1-2`.
        """
        for language in self.REPEATING:
            for source in ('10-stupňovej', '207-krát', '1-2'):
                out = convert('latex', language, source)
                assert r'\nbhyphen{}' in out, (language, source)
                assert 'rephyphen' not in out, (language, source)

    def test_a_digit_hyphen_is_untouched_where_the_rule_is_off(self, convert):
        """The quiet half: a language that did not opt in keeps what it always had."""
        for language in ('en', 'de', 'ru'):
            assert convert('latex', language, '10-stupňovej') == '10-stupňovej'

    def test_html_keeps_the_plain_hyphen(self, convert):
        """
        No Unicode character repeats a hyphen at a break -- U+00AD inserts one but does not
        repeat it -- so unlike `spacing.lua` this rule cannot serve both writers.
        """
        assert 'rephyphen' not in convert('html', 'pt', 'anti-inflamatório')

    def test_spanish_exempts_a_following_capital(self, convert):
        r"""
        RAE: "Excepto cuando la palabra que sigue es un nombre propio que empieza con mayúscula",
        because the capital already shows the hyphen is not a division mark. It matters here more
        than anywhere -- Gay-Lussac, Navier-Stokes, Bose-Einstein, Gutenberg-Richter.
        """
        assert convert('latex', 'es', 'Gay-Lussac') == 'Gay-Lussac'
        assert r'léxico\rephyphen{}semántico' in convert('latex', 'es', 'léxico-semántico')

    def test_only_spanish_exempts_a_capital(self, convert):
        """
        STN 01 6910 gives `Rakúsko-Uhorsko` and `Bratislava-Ružinov` as cases that *do* repeat,
        so the exception is Spanish's alone and must not leak into the other four.
        """
        for language in ('cs', 'sk', 'pl', 'pt'):
            assert r'Gay\rephyphen{}Lussac' in convert('latex', language, 'Gay-Lussac'), language

    def test_every_repeating_language_lowers_exhyphenpenalty(self):
        r"""
        Without this the macro is inert: its discretionary has an empty pre-break list, so
        `\exhyphenpenalty` is the only thing that decides whether the break may happen.
        """
        from core import i18n
        for language in self.REPEATING:
            assert i18n.languages[language].data['latex']['exhyphenpenalty'] < 1000

    def test_the_languages_whose_norms_forbid_it_do_not_declare_it(self):
        """
        Swept one at a time against each language's own authority, not assumed: German's
        Bindestrich doubles as the Trennstrich (Duden), French does not repeat it (OQLF),
        Hungarian repeats only in specialist works (AkH. 238), Russian usually does not
        (Milchin), Ukrainian's Правопис does not state it, and English has no such rule.
        """
        from core import i18n
        for language in ('de', 'en', 'fr', 'hu', 'ru', 'uk', 'fa'):
            typography = i18n.languages[language].data.get('typography', {})
            assert not typography.get('repeat_hyphen'), language


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


class TestArrayRowSeparatorForTheWeb:
    r"""
    `|arr` separates its rows with `\\[\jot]`, because `array` zeroes the lengths `\openup`
    raises and two rows of display-style fractions would otherwise touch.

    `\jot` is a TeX length register, and MathJax has no notion of one: it reads the bracket as a
    dimension it cannot parse and refuses the whole block with `Bracket argument to \\ must be a
    dimension`, printing that in red where the equations should be. Every one of the 125 `|arr`
    call sites in `source/` was unrenderable on the web.
    """
    BLOCK = ('$$\n    \\begin{array}{l}\n        a \\\\[\\jot]\n        b\n    \\end{array}\n$$\n')

    def test_the_web_gets_an_explicit_length(self, convert):
        assert r'\\[10pt]' in convert('html', 'en', self.BLOCK)

    def test_no_jot_survives_into_a_fragment(self, convert):
        assert r'\jot' not in convert('html', 'en', self.BLOCK)

    def test_the_booklet_keeps_the_register(self, convert):
        r"""The quiet half: LaTeX must keep `\jot`, which is the document's own setting for
        exactly this gap -- `dgs.cls` puts it at 10pt against plain LaTeX's 3pt."""
        assert r'\jot' in convert('latex', 'en', self.BLOCK)


class TestCodeIsNotExpanded:
    r"""
    `siunitx.expand` and `dgsmacros.expand` rewrite maths, and a code span is not maths.

    Markdown sets a code span and a fenced block verbatim, so a macro written in one is being
    *named* rather than called. `source/naboj/phys/errors/*.md` is prose about the sources and
    names `\qty` and `\Diff` throughout; `naboj/test/00`'s macro problems print every call in a
    `<code>` beside its own rendering, which is the whole point of those tables. Expanding there
    replaces the thing being talked about with its answer.

    The TeX writer never reaches either expander, so this is an HTML-only rule.
    """

    def test_a_macro_named_in_a_code_span_stays_as_written(self, convert):
        output = convert('html', 'en', 'Write `\\Int[0][T]{v}{t}` for an integral.')
        assert '<code>\\Int[0][T]{v}{t}</code>' in output

    def test_a_unit_named_in_a_code_span_stays_as_written(self, convert):
        output = convert('html', 'en', 'Write `\\qty{3}{\\metre}` for a length.')
        assert '<code>\\qty{3}{\\metre}</code>' in output

    def test_the_prose_around_a_code_span_is_still_expanded(self, convert):
        output = convert('html', 'en', 'Write `\\Int` to get $\\Int{x}{x}$.')
        assert '<code>\\Int</code>' in output
        assert '\\mathop{}\\!\\mathrm{d}' in output

    def test_a_fenced_block_is_left_alone(self, convert):
        output = convert('html', 'en', '~~~\n\\Int[0][T]{v}{t}\n\\qty{3}{\\metre}\n~~~\n')
        assert '\\Int[0][T]{v}{t}' in output
        assert '\\qty{3}{\\metre}' in output
        assert '\\mathop' not in output
