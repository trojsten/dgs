import datetime
import pytest

from core.filters.latex import render_list, textbf, textit, isotex, format_gender_suffix, format_people
from core.filters.numbers import nth, roman, plural


class TestRender():
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


class TestIsotex():
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
            format_gender_suffix(dict(name='Melody', gender='x'))

    def test_single_dict_m(self):
        assert format_gender_suffix(dict(name="Adam", gender='m')) == ''

    def test_single_dict_n(self):
        assert format_gender_suffix(dict(name="Kaj", gender='n')) == 'o'

    def test_single_dict_f(self):
        assert format_gender_suffix(dict(name="Viki", gender='f')) == 'a'

    def test_multi_dict(self):
        assert format_gender_suffix([dict(name="Majo", gender='m'), dict(name="Nina", gender="f")]) == 'i'

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
        assert format_people(dict(name='Adam', gender='m')) == 'Adam'

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
