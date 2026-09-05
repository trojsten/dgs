import datetime

import pytest

from core.builder.context.quantities import MissingSymbolError, PhysicsQuantity
from core.filters.latex import (
    approx_exponential,
    approx_float,
    approx_general,
    equals_exponential,
    equals_float,
    equals_general,
    format_gender_suffix,
    format_people,
    isotex,
    num,
    num_exponential,
    num_float,
    num_general,
    render_list,
    textbf,
    textit,
)
from core.filters.numbers import format_exponential, format_general, nth, plural, roman


class TestRender:
    def test_render_list_nolist(self):
        assert render_list('string') == "string"

    def test_render_list_empty(self):
        assert render_list([]) == ""

    def test_render_list_one(self):
        assert render_list(["x"]) == "x"

    def test_render_list_two(self):
        assert render_list(["x", "y"]) == "x a y"

    def test_render_list_three(self):
        assert render_list(["x", "y", "z"]) == "x, y a z"

    def test_render_list_four(self):
        assert render_list(["Hovi", "Enka", "Fek", "Lista"]) == "Hovi, Enka, Fek a Lista"

    def test_render_list_wrap(self):
        assert render_list(["Tvoja", "mama"], func=textbf) == r"\textbf{Tvoja} a \textbf{mama}"

    def test_render_list_f(self):
        assert render_list(["x", "y", "z"], func=lambda x: f'f({x})') == r"f(x), f(y) a f(z)"

    def test_render_list_f_oxford(self):
        assert (render_list(["x", "y", "z"], and_word="und", oxford_comma=True, func=lambda x: f'f({x})') ==
                r"f(x), f(y), und f(z)")


class TestIsotex:
    def test_one(self):
        assert isotex(datetime.date(2021, 9, 23)) == '2021--09--23'

    def test_no_datetime(self):
        with pytest.raises(AttributeError):
            isotex('1. 1. 1999')


@pytest.fixture
def word_masculine():
    return "plyš"


@pytest.fixture
def word_feminine():
    return "kategóri"


class TestPlural:
    def test_one(self, word_masculine):
        assert word_masculine + plural(1, "", "e", "ov") == "plyš"

    def test_two(self, word_masculine):
        assert word_masculine + plural(3, "", "e", "ov") == "plyše"

    def test_many(self, word_masculine):
        assert word_masculine + plural(10, "", "e", "ov") == "plyšov"

    def test_one_cat(self, word_feminine):
        assert word_feminine + plural(1, "a", "e", "e") == "kategória"

    def test_two_cat(self, word_feminine):
        assert word_feminine + plural(2, "a", "e", "e") == "kategórie"

    def test_many_cat(self, word_feminine):
        assert word_feminine + plural(7, "a", "e", "e") == "kategórie"


class TestRoman:
    def test_str_fails(self):
        with pytest.raises(TypeError):
            roman('ryba')

    def test_float_fails(self):
        with pytest.raises(TypeError):
            roman(3.0)

    def test_zero_fails(self):
        with pytest.raises(ValueError):
            roman(0)

    def test_too_big_fails(self):
        with pytest.raises(ValueError):
            roman(4000)

    def test_very_big_fails(self):
        with pytest.raises(ValueError):
            roman(123456)

    @pytest.mark.parametrize("ara,rom", [
        pytest.param(1, 'I'),
        pytest.param(2, 'II'),
        pytest.param(3, 'III'),
        pytest.param(9, 'IX'),
        pytest.param(49, 'XLIX'),
        pytest.param(949, 'CMXLIX'),
        pytest.param(1234, 'MCCXXXIV'),
        pytest.param(1990, 'MCMXC'),
        pytest.param(2022, 'MMXXII'),
    ])
    def test_roman(self, ara, rom):
        assert roman(ara) == rom


class TestGenderSuffix:
    def test_undefined(self):
        """ A string fails in singular case, gender is undefined """
        assert format_gender_suffix('Adam') == r'\errorMessage{?}'

    def test_many_strings(self):
        """ This should not fail: if plural, the suffix is invariably 'i' (at least in Slovak) """
        assert format_gender_suffix(['Pat', 'Mat']) == 'i'

    def test_invalid_gender(self):
        """ This fails: unknown gender """
        with pytest.raises(ValueError):
            format_gender_suffix({'name': 'Melody', 'gender': 'x'})

    def test_single_dict_m(self):
        assert format_gender_suffix({'name': "Adam", 'gender': 'm'}) == ''

    def test_single_dict_n(self):
        assert format_gender_suffix({'name': "Kaj", 'gender': 'n'}) == 'o'

    def test_single_dict_f(self):
        assert format_gender_suffix({'name': "Viki", 'gender': 'f'}) == 'a'

    def test_multi_dict(self):
        assert format_gender_suffix([{'name': "Majo", 'gender': 'm'}, {'name': "Nina", 'gender': "f"}]) == 'i'

    def test_multi_dict_str(self):
        assert format_gender_suffix(["Krto", "Zahradník", "Marcel"]) == 'i'


class TestPeople:
    def test_string(self):
        assert format_people('Adam') == 'Adam'

    def test_string_pair(self):
        assert format_people(['Tom', 'Jerry']) == 'Tom a Jerry'

    def test_string_many(self):
        assert format_people(['Mözög', 'pipka', 'pipka', 'pipka']) == 'Mözög, pipka, pipka a pipka'

    def test_single_dict(self):
        assert format_people({'name': 'Adam', 'gender': 'm'}) == 'Adam'

    def test_single_dict_list(self):
        assert format_people([{'name': 'Jaro', 'gender': 'm'}]) == 'Jaro'

    def test_pair_dict_list(self):
        assert format_people([{'name': 'Jaro', 'gender': 'm'}, "Moczo"]) == 'Jaro a Moczo'

    def test_pair_wrapped(self):
        assert format_people(["Hale", "Kala"], func=textbf) == r'\textbf{Hale} a \textbf{Kala}'

    def test_many(self):
        assert format_people(
            [
                {'name': 'Jerome', 'gender': 'm'},
                {'name': 'Harris', 'gender': 'm'},
                {'name': 'George', 'gender': 'm'},
            ]
        ) == 'Jerome, Harris a George'

    def test_girls_wrapped(self):
        assert format_people(
            [
                {'name': 'Kika', 'gender': 'f'},
                {'name': 'Emmika', 'gender': 'f'},
            ], func=textit, and_word='et'
        ) == r'\textit{Kika} et \textit{Emmika}'


class TestApproxEqualsFilters:
    """The `latex.approx_*`/`equals_*` filters just delegate to the PhysicsQuantity methods."""

    @pytest.fixture
    def q(self):
        return PhysicsQuantity.construct(96.7, 'kg', symbol='m_D')

    def test_equals_float(self, q):
        assert equals_float(q, 2) == q.equals_float(2)

    def test_equals_general(self, q):
        assert equals_general(q, 2) == q.equals_general(2)

    def test_approx_float(self, q):
        assert approx_float(q, 2) == q.approx_float(2)

    def test_approx_general(self, q):
        assert approx_general(q, 2) == q.approx_general(2)

    def test_equals_exponential(self, q):
        assert equals_exponential(q, 2) == q.equals_exponential(2)

    def test_approx_exponential(self, q):
        assert approx_exponential(q, 2) == q.approx_exponential(2)

    def test_approx_float_uses_approx_sign(self, q):
        assert r'\approx' in approx_float(q, 2)
        assert '=' not in approx_float(q, 2)

    @pytest.mark.parametrize('filt', [equals_float, equals_general, equals_exponential,
                                      approx_float, approx_general, approx_exponential])
    def test_symbol_less_quantity_raises(self, filt):
        """`(§ x|ef2 §)` on a symbol-less quantity must crash, not render `None = ...`."""
        anonymous = PhysicsQuantity.construct(96.7, 'kg')
        with pytest.raises(MissingSymbolError):
            filt(anonymous, 2)


class TestNth:
    @pytest.mark.parametrize("number,ordinal", [
        pytest.param(0, '0th'),
        pytest.param(1, '1st'),
        pytest.param(2, '2nd'),
        pytest.param(3, '3rd'),
        pytest.param(4, '4th'),
        pytest.param(10, '10th'),
        pytest.param(11, '11th'),
        pytest.param(12, '12th'),
        pytest.param(13, '13th'),
        pytest.param(16, '16th'),
        pytest.param(21, '21st'),
        pytest.param(33, '33rd'),
        pytest.param(101, '101st'),
        pytest.param(183, '183rd'),
        pytest.param(111, '111th'),
        pytest.param(341, '341st'),
    ])
    def test_nth(self, number, ordinal):
        assert nth(number) == ordinal


class TestNumFamilyIsIdempotent:
    r"""
    The `n*` filters put a bare number inside `\num{}`. Handed something that already renders as a
    siunitx call they must give it back unchanged, not wrap it again: a dimensionless quantity
    formats itself as `\num{0.0072}`, and `\num{\num{0.0072}}` is not input siunitx can parse.

    `28/enrichment` is where this surfaced. Its enrichment fractions are percentages in the
    statement and bare fractions in the algebra, and the obvious way to write that hands a
    dimensionless quantity straight to `|ng`.
    """

    @pytest.mark.parametrize('filt', [num, num_float, num_general, num_exponential])
    def test_a_plain_number_is_wrapped(self, filt):
        assert filt(0.25).startswith(r'\num{')

    @pytest.mark.parametrize('filt', [num, num_float, num_general, num_exponential])
    def test_a_dimensionless_quantity_is_not_wrapped_again(self, filt):
        q = PhysicsQuantity.construct(0.0072, '')
        out = filt(q)
        assert out.count(r'\num') == 1, out

    @pytest.mark.parametrize('filt,printed', [(num, '0.0072'), (num_float, '0.0072'),
                                              (num_general, '0.0072'), (num_exponential, '7.2')])
    def test_the_magnitude_survives(self, filt, printed):
        """`num_exponential` writes it as `7.200000e-03`; the others leave it decimal."""
        assert printed in filt(PhysicsQuantity.construct(0.0072, ''))

    @pytest.mark.parametrize('filt', [num, num_float, num_general, num_exponential])
    def test_a_dimensional_quantity_keeps_its_unit(self, filt):
        """It renders as `\\qty{…}{…}`, so wrapping it in `\\num` would lose the unit's meaning."""
        out = filt(PhysicsQuantity.construct(5, 'metre'))
        assert out.startswith(r'\qty{') and r'\metre' in out
        assert r'\num' not in out

    @pytest.mark.parametrize('filt', [num, num_float, num_general, num_exponential])
    def test_a_range_is_left_alone(self, filt):
        """`\\qtyrange` is a call of its own; the collections must survive these filters too."""
        rng = PhysicsQuantity.construct(1, 'metre') % PhysicsQuantity.construct(2, 'metre')
        assert filt(rng).startswith(r'\qtyrange{')

    def test_precision_still_reaches_the_quantity(self):
        q = PhysicsQuantity.construct(0.0072, '')
        assert num_float(q, 3) == r'\num{0.007}'

    def test_precision_still_reaches_a_plain_number(self):
        assert num_float(0.0072, 3) == r'\num{0.007}'


class TestFormatExponential:
    r"""
    `24/venus` answers `\num{1.004e-4}`. Python's `g` -- and so `format_general` -- only reaches
    for an exponent below `1e-5`, so it gives `0.0001004` instead, which is why the `e` family
    exists at all.
    """

    def test_general_keeps_this_one_decimal(self):
        """The behaviour that made the family necessary. If this ever changes, so can `e`."""
        assert format_general(1.00356e-4, 4) == '0.0001004'

    def test_exponential_does_not(self):
        assert format_exponential(1.00356e-4, 3) == '1.004e-04'

    def test_precision_counts_decimals_not_significant_figures(self):
        """Python's `e`, unlike its `g`: `|e3` is four figures, `|g3` is three."""
        assert format_exponential(1.00356e-4, 3) == '1.004e-04'
        assert format_general(1.00356e-4, 3) == '0.0001'

    def test_a_quantity_keeps_its_unit(self):
        q = PhysicsQuantity.construct(1.00356e-4, 'metre')
        assert format_exponential(q, 3) == r'\qty{1.004e-04}{\metre}'

    def test_no_precision_is_pythons_default(self):
        assert format_exponential(1.5) == '1.500000e+00'

    def test_a_string_is_a_type_error(self):
        with pytest.raises(TypeError):
            format_exponential('1.004e-4')
