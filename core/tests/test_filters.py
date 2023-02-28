import datetime
import pytest

from core.utils.filters import render_list, roman, textbf, textit, isotex, plural, get_check_digit, format_gender_suffix, format_people


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


class TestPlural():
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


class TestRoman():
    def test_roman_str(self):
        with pytest.raises(TypeError):
            roman('ryba')

    def test_roman_float(self):
        with pytest.raises(TypeError):
            roman(3.0)

    def test_roman_zero(self):
        with pytest.raises(ValueError):
            roman(0)

    def test_roman_too_big(self):
        with pytest.raises(ValueError):
            roman(123456)

    def test_roman_1(self):
        assert roman(1) == 'I'

    def test_roman_1234(self):
        assert roman(1234) == 'MCCXXXIV'

    def test_roman_49(self):
        assert roman(49) == 'XLIX'

    def test_roman_1990(self):
        assert roman(1990) == 'MCMXC'

    def test_roman_2022(self):
        assert roman(2022) == 'MMXXII'


class TestCheckDigit():
    def test_bad_string(self):
        with pytest.raises(ValueError) as exc:
            get_check_digit("Číž")
        assert "invalid literal for int()" in str(exc.value)

    def test_dict_error(self):
        with pytest.raises(AssertionError):
            get_check_digit({})

    def test_creation_1(self):
        assert get_check_digit("6739") == 9

    def test_creation_1(self):
        assert get_check_digit("PRASA") == 2


class TestGenderSuffix:
    def test_undefined(self):
        """ A string fails in singular case, undefined gender """
        assert format_gender_suffix('Adam') == r'\errorMessage{?}'

    def test_many_strings(self):
        """ This should not fail: if plural, suffix is invariably 'i' (at least in Slovak) """
        assert format_gender_suffix(['Pat', 'Mat']) == 'i'

    def test_invalid_gender(self):
        """ This fails: unknown gender """
        with pytest.raises(ValueError):
            format_gender_suffix(dict(name='Melody', gender='x'))

    def test_single_dict_m(self):
        assert format_gender_suffix(dict(name="Adam", gender='m')) == ''

    def test_single_dict_n(self):
        assert format_gender_suffix(dict(name="Tete", gender='n')) == 'o'

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
        assert format_people(['Terka', 'zub', 'zub', 'zub']) == 'Terka, zub, zub a zub'

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
