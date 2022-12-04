import datetime
import pytest

from core.utils.filters import render_list, roman, textbf, isotex, plural, get_check_digit


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
