r"""
The text-level repairs in `maths.py`.

Each rule gets a case that fires **and** a case that looks like it and must stay quiet. The
quiet halves are not padding: every one of them is a false positive an earlier spelling of
the same rule actually produced on these eight booklets.
"""

from tools.ancient.pdf import maths


class TestAccents:
    def test_prefix_is_the_normal_form(self):
        # TeX sets the accent's origin just left of its letter, so this is what the trace
        # almost always gives: `m`@343.1, arrow@354.0, `v`@354.5 in `07.pdf` page 14.
        assert maths.accents(r'm\vec v') == r'm\vec{v}'

    def test_accent_takes_the_letter_after_it_not_before(self):
        # The regression this exists for. As one alternation the suffix branch starts a
        # character earlier and wins, giving `\vec{m} v` -- the arrow on the mass instead of
        # the velocity, which is a different physical claim, and a silent one.
        assert maths.accents(r'hybnost \vec p = m\vec v') == r'hybnost \vec{p} = m\vec{v}'

    def test_a_stranded_accent_still_lands(self):
        assert maths.accents(r'B\vec') == r'\vec{B}'

    def test_greek_is_a_symbol_too(self):
        assert maths.accents(r'\vec\omega') == r'\vec{\omega}'

    def test_an_accent_already_placed_is_left_alone(self):
        # The suffix pass must not fire on what the prefix pass just wrote, or it swallows
        # the symbol in front of it as well.
        assert maths.accents(r'm\vec{v}') == r'm\vec{v}'

    def test_nothing_to_do(self):
        assert maths.accents(r'p = mv') == r'p = mv'


class TestComposites:
    def test_doteq_loses_the_equals_it_was_struck_over(self):
        assert maths.composites(r'= \doteq 251') == r'\doteq 251'

    def test_either_order(self):
        assert maths.composites(r'\doteq= 10') == r'\doteq 10'

    def test_notin_loses_its_stroke(self):
        assert maths.composites(r'V\notin/\langle V_{1}') == r'V\notin\langle V_{1}'

    def test_a_real_equals_survives(self):
        assert maths.composites(r'v = 10') == r'v = 10'

    def test_a_real_solidus_survives(self):
        # `\in` is not `\notin`, so the slash here is a division and must stay.
        assert maths.composites(r'x\in A, v = s/t') == r'x\in A, v = s/t'


class TestDifferences:
    def test_delta_before_a_variable_is_a_finite_difference(self):
        assert maths.differences(r'\Delta t') == r'\FDiff{t}'

    def test_a_lone_delta_is_the_letter(self):
        assert maths.differences(r'\Delta = 5') == r'\Delta = 5'


class TestPintUnit:
    r"""
    What may be hoisted into `values:`, which pint reads and `units.py` does not.

    Every rejection below is a quantity that reached a `meta.yaml` before this gate existed.
    """

    def test_the_exponent_form_becomes_a_solidus(self):
        # The booklets write a metre per second as `ms^{-1}`. pint reads that same string as
        # one over a millisecond -- wrong by nine orders of magnitude, and silent.
        assert maths.pint_unit('ms^{-1}') == 'm/s'

    def test_a_plain_unit_passes(self):
        assert maths.pint_unit('kg') == 'kg'

    def test_the_speed_of_light_is_not_a_unit_to_hoist(self):
        # `08/p30` gives v = 0.2c, which is good physics. pint reads `c` as the speed of light
        # and renders it `\speed_of_light`, which is not TeX, and the build stopped there.
        assert maths.pint_unit('c') is None

    def test_a_unit_the_corpus_never_writes_is_refused(self):
        # A fountain came out playing at two hectograms, because pint knows `hg`.
        assert maths.pint_unit('hg') is None

    def test_a_compound_that_did_not_split_is_refused(self):
        # A spring constant is N/m; `Nm` is a newton-metre, which is a different quantity.
        assert maths.pint_unit('Nm') is None


class TestAssignment:
    def test_a_given_quantity_is_hoisted(self):
        assert maths.assignment('s=100km') == ('s', 's', '100', 'km')

    def test_a_decimal_comma_becomes_a_point(self):
        # These booklets are Slovak and write `1,5`; YAML and pint want `1.5`.
        assert maths.assignment('t=1,5h')[2] == '1.5'

    def test_a_formula_is_not_a_given_quantity(self):
        assert maths.assignment('E=mc^{2}') is None

    def test_a_bare_number_is_not_one_either(self):
        assert maths.assignment('f = 0,1') is None


class TestUnicodeMaths:
    r"""
    What a font with readable glyph names hands back, spelled as TeX.

    Only `11.pdf` names its fonts well enough for mupdf to resolve them, so these characters
    reach the text from that booklet alone -- and none of the encoding tables ever sees them.
    """

    def test_a_minus_sign_becomes_a_hyphen(self):
        assert maths.unicode_maths('v−5') == 'v-5'

    def test_the_degree_ring_becomes_a_macro(self):
        assert maths.unicode_maths('30◦') == r'30\circ'

    def test_greek_becomes_a_macro(self):
        assert maths.unicode_maths('α') == r'\alpha'

    def test_a_macro_is_kept_off_the_letter_after_it(self):
        # `\kappav` is a different control word, and an undefined one: the build stops there.
        assert maths.unicode_maths('κv') == r'\kappa v'

    def test_ascii_maths_is_untouched(self):
        assert maths.unicode_maths('v = 5 - 3') == 'v = 5 - 3'


class TestPunctuationRuns:
    r"""
    A maths run that is only punctuation, and what decides whether it stays maths.

    `11.pdf` sets a decimal comma, a unit solidus and the `.` of a compound unit in maths
    mode, so `4,2 kJ.kg` arrived as `4$,$2 kJ$.$kg`.
    """

    def test_a_comma_inside_a_number_is_prose(self):
        assert maths.is_punctuation(',', '4')

    def test_a_solidus_inside_a_unit_is_prose(self):
        assert maths.is_punctuation('/', 'km')

    def test_a_solidus_standing_alone_is_a_symbol(self):
        # `04/p04` writes "klesá nadol so zrýchlením $/$" -- the character stands in for a
        # symbol the decode could not read, and unwrapping it hides that from the reader.
        assert not maths.is_punctuation('/', 'zrýchlením ')

    def test_nothing_before_it_is_not_attached_either(self):
        assert not maths.is_punctuation('.', '')

    def test_a_formula_is_never_punctuation(self):
        assert not maths.is_punctuation('v = 5', '4')


class TestDegrees:
    r"""
    `\ang{}` is the house spelling, and `^\circ` is a build error rather than a warning:
    `convertor.py` carries a `RegexFailure` for it.
    """

    def test_inside_a_formula(self):
        assert maths.degrees(r'$\alpha = 30^{\circ}$') == r'$\alpha = \ang{30}$'

    def test_split_across_the_run_boundary(self):
        # The ring is set in `cmsy` and the number in the prose face, so where the two do not
        # share a maths run the line arrives as `30$^{\circ}$`.
        assert maths.degrees('30$^{\\circ}$ a') == r'$\ang{30}$ a'

    def test_a_bare_circ_is_left_alone(self):
        # `\circ` with no number in front of it is composition, not a degree.
        assert maths.degrees(r'$f \circ g$') == r'$f \circ g$'


class TestQuantities:
    r"""What may become a `\qty{}`, and in what spelling."""

    def test_a_number_against_a_unit(self):
        assert maths.quantities('100km')[0] == r'\qty{100}{\kilo\metre}'

    def test_the_decimal_comma_becomes_a_point(self):
        # siunitx parses the number and refuses a comma -- `Invalid number '88,10'` stopped
        # volume 08's booklet. It puts the comma back on the page from the locale.
        assert maths.quantities('88,10kmh^{-1}')[0] == r'\qty{88.10}{\kilo\metre\per\hour}'

    def test_a_bare_ms_is_reported_not_converted(self):
        # `ms` is a millisecond to `units.py` and a lost `ms^{-1}` in these booklets, so a
        # boat's speed became a duration. Refused and reported; the prose keeps it as written.
        body, missing = maths.quantities('0,954ms')
        assert body == '0,954ms' and missing == ['ms']

    def test_the_reciprocal_form_still_converts(self):
        assert maths.quantities('5ms^{-1}')[0] == r'\qty{5}{\metre\per\second}'

    def test_a_bare_letter_is_never_a_unit(self):
        # Adjacency to a number is the whole rule; `s` here is a variable.
        assert maths.quantities('s = v t')[0] == 's = v t'


class TestScriptsOnce:
    def test_a_repeated_superscript_is_rebased(self):
        assert maths.scripts_once('a^{1}^{2}') == 'a^{1}{}^{2}'

    def test_across_an_intervening_subscript(self):
        assert maths.scripts_once(r'a^{A}_{B}^{C}') == r'a^{A}_{B}{}^{C}'

    def test_a_nested_argument_is_walked_not_guessed(self):
        assert (maths.scripts_once(r'-^{\frac{1}{2}6}_{-1}^{13}')
                == r'-^{\frac{1}{2}6}_{-1}{}^{13}')

    def test_one_of_each_is_left_alone(self):
        assert maths.scripts_once('v_{0}^{2}') == 'v_{0}^{2}'

    def test_a_new_base_starts_over(self):
        assert maths.scripts_once('x^2y^3') == 'x^2y^3'


class TestSeparateMacros:
    r"""
    TeX reads a control word as the longest run of letters after the backslash, so a Greek
    letter butted against a variable is one undefined macro. The glyph stream has no spaces in
    it, so the decode produces these constantly.
    """

    def test_a_greek_letter_and_a_variable(self):
        assert maths.separate_macros(r'\betao') == r'\beta o'

    def test_inside_a_fraction(self):
        assert maths.separate_macros(r'\frac{2\pil}{v}') == r'\frac{2\pi l}{v}'

    def test_a_complete_macro_is_left_alone(self):
        assert maths.separate_macros(r'\Rightarrow') == r'\Rightarrow'

    def test_the_longest_known_prefix_wins(self):
        # `\pi` is a macro and so is `\pm`; splitting `\pil` at one letter would give `\p il`.
        assert maths.separate_macros(r'\pil') == r'\pi l'

    def test_an_unknown_control_word_is_not_cut_at_a_guess(self):
        assert maths.separate_macros(r'\unknownthing') == r'\unknownthing'


class TestBareAccentsAndRoots:
    def test_a_radical_with_no_radicand(self):
        assert maths.radicals(r'\sqrt') == r'\sqrt{}'

    def test_an_arrow_with_nothing_under_it(self):
        assert maths.radicals(r'\vec') == r'\vec{}'

    def test_a_radicand_is_left_alone(self):
        assert maths.radicals(r'\sqrt{2}') == r'\sqrt{2}'

    def test_an_accented_symbol_is_left_alone(self):
        assert maths.radicals(r'\vec{v}') == r'\vec{v}'


class TestStrayMarks:
    def test_a_caron_that_reached_a_formula_is_dropped(self):
        # XeTeX gives some Unicode letters catcode 11, so this was read as part of the control
        # word before it and stopped volume 09 on an undefined `\wpˇ`.
        assert maths.strip_marks('MG\\wpˇ') == 'MG\\wp'

    def test_prose_letters_are_untouched(self):
        assert maths.strip_marks('v_{max}') == 'v_{max}'
