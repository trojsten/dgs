r"""
This repository's own macros expanded into ordinary TeX, which is what the web gets.

The reason this exists rather than a pile of MathJax macros is exactly `test_siunitx`'s: a
MathJax macro is a fixed-arity substitution, and this vocabulary is not. `\Int[0][T]{v}{t}` has
two optional arguments before two mandatory ones, `\Expected{X}[n]` has one *after* a mandatory
one, `\FDiff^{2}_{\text{vap}}{H}` has an embellishment that takes `^` and `_` in either order,
and `\Coord{-d; d}` has one argument that must be split. Each of those shapes has a test here.

Every expansion is read off `core/latex/math.tex`, so the page and the booklet agree; several of
the cases below are a defect that was repaired in both at once, and they are here so that
repairing one and not the other goes red.

The quiet half matters as much as the firing half. A macro *named* with no arguments is prose
about the source and must come back untouched -- `errors/*.md` is written in that register
throughout, and `test/00` prints every call beside its own rendering.
"""
import pytest

from core.filters.dgsmacros import expand


class TestTheShapesAMacroCannotDo:
    """The four that justify a parser. Each is a form no fixed-arity macro can take."""

    def test_optional_arguments_before_mandatory_ones(self):
        assert expand(r'\Int[0][T]{v(t)}{t}') == r'\int \limits_{0}^{T}v(t)\mathop{}\!\mathrm{d} t'

    def test_an_optional_argument_after_a_mandatory_one(self):
        assert expand(r'\Expected{X}[n]') == r'\mathrm{E}\left[X\right]_{n}'

    def test_an_embellishment_in_either_order(self):
        both = r'\mathop{}\!\Delta ^{2}_{\text{vap}}H'
        assert expand(r'\FDiff^{2}_{\text{vap}}{H}') == both
        assert expand(r'\FDiff_{\text{vap}}^{2}{H}') == both

    def test_an_argument_split_on_semicolons(self):
        assert expand(r'\Coord{-d; d}') == r'\left[-d;d\right]'
        assert expand(r'\Tuple{a; b; c}') == r'\left(a;b;c\right)'


class TestWhatItLeavesAlone:
    """Half the correctness here is not firing. Each of these looks like a call and is not."""

    def test_a_macro_named_without_arguments_is_untouched(self):
        assert expand(r'the \Int family') == r'the \Int family'
        assert expand(r'\IIntI with no power') == r'\IIntI with no power'

    def test_an_unbalanced_argument_is_left_exactly_as_it_was(self):
        """A visible `\\Int` beats a silently mangled integral."""
        assert expand(r'\Int[0][T]{v(t)') == r'\Int[0][T]{v(t)'

    def test_a_macro_this_repository_does_not_define_is_untouched(self):
        assert expand(r'\frac{1}{2}') == r'\frac{1}{2}'
        assert expand(r'\sum_{i}^{n} x_i') == r'\sum_{i}^{n} x_i'

    def test_text_with_no_macros_comes_back_identical(self):
        assert expand(r'\alpha = \beta + 1') == r'\alpha = \beta + 1'


class TestAgreementWithMathTex:
    """Cases where `math.tex` was repaired and the expansion has to carry the repair."""

    def test_the_derivative_order_goes_on_both_halves(self):
        """`\\Derivative[2]{f}{x}` set `d^2 f / d x` until the macro was fixed."""
        assert expand(r'\Derivative[2]{f}{x}') == r'\frac{\mathrm{d}^{2}f}{\mathrm{d}x^{2}}'

    def test_an_indexed_integral_without_a_power_has_no_empty_superscript(self):
        """`\\IIntI[S]{B}{S}` emitted `\\diff^{}`, which TeX draws as a plain `d`."""
        assert expand(r'\IIntI[S]{\vec{B}}{S}') == (
            r'\iint \limits_{S}\vec{B}\mathop{}\!\mathrm{d} S')
        assert expand(r'\IIntI[S]{\vec{B}}[2]{S}') == (
            r'\iint \limits_{S}\vec{B}\mathop{}\!\mathrm{d}^{2} S')

    def test_the_expected_value_subscripts_the_whole_index(self):
        """`\\Expected{X}[12]` subscripted only the `1`, because `_#2` takes one token."""
        assert expand(r'\Expected{X}[12]') == r'\mathrm{E}\left[X\right]_{12}'


class TestTheParserItself:
    def test_a_mandatory_argument_may_be_a_bare_token(self):
        """xparse takes one token for `m`, so `\\Diff t` is legal and is written."""
        assert expand(r'\Diff t') == r'\mathop{}\!\mathrm{d}t'
        assert expand(r'\Diff\alpha') == r'\mathop{}\!\mathrm{d}\alpha'
        assert expand(r'\frac{\Diff I}{I}') == r'\frac{\mathop{}\!\mathrm{d}I}{I}'

    def test_a_control_word_is_kept_off_the_letter_that_follows_it(self):
        """`\\partial` welded to `u` is the undefined `\\partialu`."""
        assert expand(r'\FDiff{H}') == r'\mathop{}\!\Delta H'
        assert expand(r'\PDrv{u}{x}') == r'\frac{\partial u}{\partial x}'
        assert expand(r'\IntX{f}') == r'\int f'

    def test_nested_braces_are_counted(self):
        assert expand(r'\Int{\frac{a}{b}}{x}') == (
            r'\int \frac{a}{b}\mathop{}\!\mathrm{d} x')

    def test_several_calls_on_one_line(self):
        assert expand(r'\Diff{x} and \Diff{y}') == (
            r'\mathop{}\!\mathrm{d}x and \mathop{}\!\mathrm{d}y')

    def test_a_missing_optional_argument_prints_no_empty_bound(self):
        """`\\limits_{}` is legal and ugly; an absent bound is simply left off."""
        assert expand(r'\Int{x^2}{x}') == r'\int x^2\mathop{}\!\mathrm{d} x'


class TestTheStandInSymbols:
    def test_the_surface_integrals_are_operators(self):
        r"""
        `\oiint` is `esint`'s and MathJax has not got it, so a character stands in -- and it has
        to be `\mathop`, because `\limits` is legal only on an operator and MathJax says so in
        yellow across the whole display.
        """
        assert expand(r'\OIIntI[S]{E}{S}').startswith(r'\mathop{\unicode{x222F}}\limits_{S}')


@pytest.mark.parametrize('call, expected', [
    (r'\IntDV[S]{B}{S}', r'\int \limits_{S}\vec{B} \cdot \mathop{}\!\mathrm{d} \vec{S}'),
    (r'\IntP[0][1]{a + b}{x}', r'\int \limits_{0}^{1}\left(a + b\right)\mathop{}\!\mathrm{d} x'),
    (r'\OInt[C]{E}{l}', r'\oint \limits_{C}E\mathop{}\!\mathrm{d} l'),
    (r'\SumP[i][n]{a + b}', r'\sum\limits_{i}^{n}{\left(a + b\right)}'),
    (r'\Log[2]{x}', r'\log_{2}{x}'),
    (r'\Nuclide[14][6]{C}', r'{}^{14}_{6}\mathrm{C}'),
    (r'\Eval{F(x)}{a}[b]', r'\left.F(x)\right|_{a}^{b}'),
    (r'\Distribution{N}[x]{\mu}', r'N\left(x \mid \mu\right)'),
    (r'\Set{1,2,3}[n]', r'\left\{1,2,3\right\}_{n}'),
    (r'\Max[i]{a_i}', r'\max\limits_{i}{a_i}'),
    (r'\DrvEval{f}{x}{x=0}', r'\left.\frac{\mathrm{d}f}{\mathrm{d}x}\right|_{x=0}'),
])
def test_one_member_of_each_family(call, expected):
    assert expand(call) == expected
