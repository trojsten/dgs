import math
import pytest
import itertools

from core.utilities.lists import split_mod, split_div, split_callback, numerate, add_numbers


def is_prime(what: int) -> int:
    if not type(what) is int or what < 2:
        return 0
    else:
        return int(all(what % x != 0 for x in range(2, math.isqrt(what) + 1)))


@pytest.fixture
def shopping_list():
    return ["Javelin", "HIMARS", "ATACMS"]

@pytest.fixture
def folk_heroes():
    return [
        dict(language="sk", name="Jánošík"),
        dict(language="cs", name="Krakonoš"),
        dict(language="hu", name="Rózsa Sándor"),
    ]

@pytest.fixture
def primes():
    def _generator():
        for i in itertools.count(2, 1):
            if is_prime(i):
                yield i

    return _generator

@pytest.fixture
def fibonacci():
    def _generator():
        a, b = 0, 1
        for i in itertools.count():
            yield a
            a, b = b, a + b

    return _generator


class TestSplits():
    def test_splitmod(self):
        assert split_mod(list(range(0, 12)), 3) == [[0, 3, 6, 9], [1, 4, 7, 10], [2, 5, 8, 11]]

    def test_splitmod_2(self):
        assert split_mod(list(range(0, 17)), 5) == [[0, 5, 10, 15], [1, 6, 11, 16], [2, 7, 12], [3, 8, 13], [4, 9, 14]]

    def test_splitmod_first_one(self):
        assert split_mod(list(range(1, 12)), 3, first=1) == [[3, 6, 9], [1, 4, 7, 10], [2, 5, 8, 11]]

    def test_splitdiv_empty(self):
        assert split_div([], 2) == []

    def test_splitdiv_ragged(self):
        assert split_div(['a', 'b', 'c'], 2) == [['a', 'b'], ['c']]

    def test_splitdiv_generator(self):
        assert split_div(range(0, 12), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]

    def test_splitdiv_list(self):
        assert split_div(list(range(0, 12)), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]

    def test_splitdiv_list2(self):
        assert split_div(list(range(0, 17)), 5) == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13, 14], [15, 16]]

    def test_split_callback(self):
        assert split_callback(list(range(0, 12)), is_prime, 2) == [[0, 1, 4, 6, 8, 9, 10], [2, 3, 5, 7, 11]]

    def test_split_callback_prime(self):
        assert split_callback(list(range(0, 12)), is_prime, 3) == [[0, 1, 4, 6, 8, 9, 10], [2, 3, 5, 7, 11], []]

    def test_split_callback_low_count(self):
        with pytest.raises(IndexError):
            split_callback(list(range(0, 12)), is_prime, 1)


class TestAdornments():
    def test_add_numbers(self, shopping_list):
        assert add_numbers(shopping_list) == [
            dict(number=0, id="Javelin"),
            dict(number=1, id="HIMARS"),
            dict(number=2, id="ATACMS"),
        ]

    def test_add_numbers_start(self, shopping_list):
        assert add_numbers(shopping_list, itertools.count(4, 1)) == [
            dict(number=4, id="Javelin"),
            dict(number=5, id="HIMARS"),
            dict(number=6, id="ATACMS"),
        ]

    def test_add_primes(self, shopping_list, primes):
        assert add_numbers(shopping_list, primes()) == [
            dict(number=2, id="Javelin"),
            dict(number=3, id="HIMARS"),
            dict(number=5, id="ATACMS"),
        ]

    def test_add_numbers_dictlist(self, folk_heroes):
        assert add_numbers(folk_heroes, itertools.count(4, 1)) == [
            dict(number=4, id=dict(language="sk", name="Jánošík")),
            dict(number=5, id=dict(language="cs", name="Krakonoš")),
            dict(number=6, id=dict(language="hu", name="Rózsa Sándor")),
        ]

    def test_numerate(self, folk_heroes):
        assert numerate(folk_heroes) == [
            dict(number=0, language="sk", name="Jánošík"),
            dict(number=1, language="cs", name="Krakonoš"),
            dict(number=2, language="hu", name="Rózsa Sándor"),
        ]

    def test_numerate_primes(self, folk_heroes, fibonacci):
        assert numerate(folk_heroes, itertools.islice(fibonacci(), 5, None)) == [
            dict(number=5, language="sk", name="Jánošík"),
            dict(number=8, language="cs", name="Krakonoš"),
            dict(number=13, language="hu", name="Rózsa Sándor"),
        ]

    def test_numerate_error(self, shopping_list):
        with pytest.raises(AssertionError):
            numerate(shopping_list)

