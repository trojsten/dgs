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


class TestSpecials:
    r"""
    Pandoc escapes TeX specials in prose and passes a `$...$` body through untouched, so these
    have to be escaped here or not at all.
    """

    def test_a_percent_sign_would_otherwise_comment_out_the_rest(self):
        # `02/p34` asks about a 50 % alcohol and printed `Majme 50 alkohol` -- the sign gone
        # and the closing delimiter pushed to the next line, with no warning anywhere.
        assert maths.specials('50%') == r'50\%'

    def test_an_ampersand_and_a_hash(self):
        assert maths.specials('a&b') == r'a\&b'
        assert maths.specials('x#1') == r'x\#1'

    def test_an_escape_is_not_doubled(self):
        assert maths.specials(r'50\%') == r'50\%'

    def test_a_macro_is_untouched(self):
        assert maths.specials(r'\frac{1}{2}') == r'\frac{1}{2}'


class TestPercent:
    r"""A percentage is a quantity, and the repository writes it `\qty{N}{\percent}`."""

    def test_inside_a_formula(self):
        assert maths.percents('50%') == r'\qty{50}{\percent}'

    def test_the_decimal_comma_is_normalised(self):
        assert maths.percents('7,5%') == r'\qty{7.5}{\percent}'

    def test_an_escaped_sign_too(self):
        assert maths.percents(r'50\%') == r'\qty{50}{\percent}'

    def test_left_in_the_prose_it_gets_its_delimiters(self):
        assert maths.prose_percents('o 10% menšie') == r'o $\qty{10}{\percent}$ menšie'

    def test_maths_spans_are_left_to_the_other_rule(self):
        # `in_prose` must not reach inside `$...$`, which `tidy` has already handled.
        assert maths.prose_percents(r'$x = 5\%$ a') == r'$x = 5\%$ a'

    def test_a_bare_sign_with_no_number_is_not_a_quantity(self):
        # `Koľko % hmotnosti` is prose asking "what percentage", not a value.
        assert maths.prose_percents('Koľko % hmotnosti') == 'Koľko % hmotnosti'


class TestProseWords:
    def test_an_accented_word_is_prose(self):
        # `06/earth-falls` sets `$T^2/a^3 = konšt.$`. MinionPro's maths cuts have no `š`, so
        # the letter left the page while the build stayed green -- six times over.
        assert maths.prose_words('T^{2}/a^{3} = konšt.') == r'T^{2}/a^{3} = \text{konšt.}'

    def test_the_abbreviating_stop_comes_along(self):
        assert maths.prose_words('konšt.') == r'\text{konšt.}'

    def test_an_ascii_word_is_left_alone(self):
        # The narrow rule, deliberately: `mgh` and `sin` are set perfectly well by the maths
        # font, and deciding whether an ASCII run is a word or a product of variables is a
        # judgement per site rather than something a sweep may take.
        assert maths.prose_words('mgh') == 'mgh'

    def test_a_control_word_is_not_a_word(self):
        assert maths.prose_words(r'\alpha+\beta') == r'\alpha+\beta'

    def test_a_subscript_already_wrapped_is_not_wrapped_twice(self):
        assert maths.prose_words(r'\text{konšt.}') == r'\text{konšt.}'

    def test_a_greek_letter_spelled_out_in_unicode_is_a_symbol_not_a_word(self):
        # `unicode_maths` has already turned these into control words by the time `tidy`
        # reaches here; one that slipped through must not become `\text{α}`, which would set
        # it upright and in the text font.
        assert maths.prose_words(r'\alpha') == r'\alpha'


class TestKnownMacros:
    def test_the_hand_read_tables_are_collected_too(self):
        # `\leqslant` lives only in `glyphs/03.yaml`. Collected from `encodings` alone,
        # `separate_macros` knew `\leq` and split the word at the longest prefix it did know,
        # giving `$\mu_1 \leq slant F\cos\alpha$` -- which compiles, and prints `slant`.
        assert 'leqslant' in maths.KNOWN_MACROS
        assert 'varkappa' in maths.KNOWN_MACROS
        assert maths.separate_macros(r'\mu_{1}\leqslant F') == r'\mu_{1}\leqslant F'

    def test_a_word_butted_onto_a_shorter_macro_still_separates(self):
        assert maths.separate_macros(r'\betao') == r'\beta o'


class TestUprightUnits:
    def test_a_unit_set_upright_converts(self):
        assert maths.quantities('100km', frozenset({'km'}))[0] == r'\qty{100}{\kilo\metre}'

    def test_a_symbol_set_in_maths_italic_does_not(self):
        # `05/switch-charge` prints *"na kondenzátore 3C"* -- a capacitor of capacitance `3C`,
        # not a charge of three coulombs. Adjacency to a number was the whole old rule, and
        # across the archive 383 such pairs are italic against 237 upright.
        assert maths.quantities('2C', frozenset())[0] == '2C'
        assert maths.quantities('2g', frozenset())[0] == '2g'

    def test_a_token_ambiguous_within_one_run_is_left_alone(self):
        # `_upright_units` omits a token it saw set both ways, and omission means no `\qty`.
        assert maths.quantities('5m', frozenset({'km'}))[0] == '5m'

    def test_with_no_information_it_behaves_as_before(self):
        # `None` is not the empty set: a caller that cannot say keeps the old behaviour.
        assert maths.quantities('100km')[0] == r'\qty{100}{\kilo\metre}'

    def test_a_given_quantity_is_only_hoisted_when_its_unit_is_upright(self):
        assert maths.assignment('s = 100km', frozenset({'km'})) is not None
        assert maths.assignment('a = 2g', frozenset()) is None


class TestTemperatures:
    def test_a_ring_with_c_after_it_is_celsius_not_an_angle(self):
        # `\ang{100}C` left a loose `C` for the unit rule to read as a coulomb, which is how
        # `02/alcohol`'s water came to boil at a hundred coulombs.
        assert maths.degrees(r'100^{\circ}C') == r'\qty{100}{\celsius}'

    def test_the_ring_needs_no_caret(self):
        # The ring is a `cmsy` glyph and is not always raised in the stream.
        assert maths.degrees(r'100\circC') == r'\qty{100}{\celsius}'

    def test_a_plain_angle_stays_an_angle(self):
        assert maths.degrees(r'30^{\circ}') == r'\ang{30}'

    def test_the_maths_delimiters_survive(self):
        # A pattern that simply ate the `$` left the line with an unbalanced one.
        out = maths.degrees(r'nedosiahne $100\circ$C a voda')
        assert out == r'nedosiahne $\qty{100}{\celsius}$ a voda'
        assert out.count('$') % 2 == 0

    def test_a_word_beginning_with_c_is_not_a_unit(self):
        # `2Celková` -- a sentence opening after a formula, three times in the archive.
        assert maths.degrees(r'\ang{0}Celkova') == r'\ang{0}Celkova'

    def test_composition_is_not_a_degree(self):
        assert maths.degrees(r'f\circ g') == r'f\circ g'


class TestStrandedRings:
    def test_a_ring_with_no_base_becomes_a_hole(self):
        assert maths.stranded_rings(r'$^{\circ}$', r'\errorMessage{math}') == \
            r'$\errorMessage{math}$'

    def test_a_script_that_has_a_base_is_left_alone(self):
        assert maths.stranded_rings(r'$x^{2}$', r'\errorMessage{math}') == r'$x^{2}$'
        assert maths.stranded_rings(r'$\frac{h}{s}_{\circ}$', r'\errorMessage{math}') == \
            r'$\frac{h}{s}_{\circ}$'


class TestReciprocalUnits:
    r"""`ms^{-1}` is how these booklets write a speed, and the exponent is what identifies it."""

    def test_the_first_power(self):
        assert maths._reciprocal('kmh^{-1}') == 'km/h'

    def test_higher_powers_too(self):
        # Only `^{-1}` used to convert, which left an acceleration and a density as prose while
        # a speed beside them became a quantity.
        assert maths._reciprocal('ms^{-2}') == 'm/s^2'
        assert maths._reciprocal('kgm^{-3}') == 'kg/m^3'

    def test_a_split_that_names_no_unit_is_refused(self):
        # The quiet case: `_reciprocal` only accepts a split the table actually holds, so a
        # variable with a reciprocal exponent stays algebra.
        assert maths._reciprocal('M^{-1}') is None
        assert maths._reciprocal('zz^{-1}') is None

    def test_a_unit_without_an_exponent_is_not_its_business(self):
        assert maths._reciprocal('km') is None

    def test_the_exponent_settles_it_without_the_font(self):
        # A unit the author set in maths italic is still a unit: the upright test decides a
        # bare `2C`, and has nothing left to decide once a reciprocal exponent is present.
        assert maths.quantities(r'15ms^{-1}', frozenset())[0] == r'\qty{15}{\metre\per\second}'

    def test_an_italic_symbol_is_still_refused(self):
        assert maths.quantities('2C', frozenset())[0] == '2C'
