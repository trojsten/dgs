import datetime
import pytest

from core.filters.latex import (nth, render_list, roman, textbf, textit, isotex, plural,
                                format_gender_suffix, format_people)


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


class TestGenderSuffix:
    def test_undefined(self):
        """ A string fails in singular case, undefined gender """
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
    def test_zeroth(self):
        assert nth(0) == "0th"

    def test_first(self):
        assert nth(1) == "1st"

    def test_second(self):
        assert nth(2) == "2nd"

    def test_third(self):
        assert nth(3) == "3rd"

    def test_fourth(self):
        assert nth(4) == "4th"

    def test_tenth(self):
        assert nth(10) == "10th"

    def test_eleventh(self):
        assert nth(11) == "11th"

    def test_twelfth(self):
        assert nth(12) == "12th"

    def test_thirteenth(self):
        assert nth(13) == "13th"

    def test_sixteenth(self):
        assert nth(16) == "16th"

    def test_twentyfirst(self):
        assert nth(21) == "21st"

    def test_thirtythird(self):
        assert nth(33) == "33rd"

    def test_101(self):
        assert nth(101) == "101st"

    def test_183(self):
        assert nth(183) == "183rd"


