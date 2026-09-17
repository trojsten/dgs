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
