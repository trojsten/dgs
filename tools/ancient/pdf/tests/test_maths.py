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
