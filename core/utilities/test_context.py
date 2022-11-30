import pytest
from pprint import pprint as pp
from .context import Context, split_mod, split_div, split_callback, is_prime


class TestSplits():
    def test_splitmod(self):
        assert split_mod(list(range(0, 12)), 3) == [[0, 3, 6, 9], [1, 4, 7, 10], [2, 5, 8, 11]]

    def test_splitmod_2(self):
        assert split_mod(list(range(0, 17)), 5) == [[0, 5, 10, 15], [1, 6, 11, 16], [2, 7, 12], [3, 8, 13], [4, 9, 14]]

    def test_splitdiv(self):
        assert split_div(list(range(0, 12)), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]

    def test_splitdiv_2(self):
        assert split_div(list(range(0, 17)), 5) == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13, 14], [15, 16]]

    def test_split_callback(self):
        assert split_callback(list(range(0, 12)), is_prime, 2) == [[0, 1, 4, 6, 8, 9, 10], [2, 3, 5, 7, 11]]

    def test_split_callback_prime(self):
        assert split_callback(list(range(0, 12)), is_prime, 3) == [[0, 1, 4, 6, 8, 9, 10], [2, 3, 5, 7, 11], []]

    def test_split_callback_bad_count(self):
        with pytest.raises(IndexError):
            split_callback(list(range(0, 12)), is_prime, 1)


@pytest.fixture
def context_empty():
    return Context()

@pytest.fixture
def context_defaults():
    return Context(foo='bar', baz=5)

@pytest.fixture
def context_two():
    return Context(foo='hotel', qux=7)

@pytest.fixture
def context_old():
    pp(Context().data)
    return Context(boss='Dušan', pictures='Plyš', htr='Kvík')

@pytest.fixture
def context_new():
    return Context(boss='Marcel', pictures='Terka', nothing='Nina')

@pytest.fixture
def context_override(context_empty, context_old, context_new):
    context_empty.adopt('fks', context_old)
    context_empty.adopt('fks', context_new)
    return context_empty

@pytest.fixture
def context_numbered():
    return Context()


class TestContext():
    def test_empty(self, context_empty):
        assert context_empty.data == {}

    def test_empty_nothing(self, context_defaults):
        with pytest.raises(KeyError):
            _ = context_defaults.data['boo']

    def test_default(self, context_defaults):
        assert context_defaults.data == {'foo': 'bar', 'baz': 5}

    def test_adopt_override(self, context_override):
        assert context_override.data['fks']['pictures'] == 'Terka'

    def test_adopt_no_override(self, context_override):
        assert context_override.data['fks']['htr'] == 'Kvík'

    def test_adopt_new(self, context_override):
        assert context_override.data['fks']['nothing'] == 'Nina'

    def test_adopt_full(self, context_override):
        assert context_override.data == dict(fks=dict(boss='Marcel', pictures='Terka', htr='Kvík', nothing='Nina'))

    def test_add_id(self, context_defaults):
        context_defaults.add_id(4)
        assert context_defaults.data['id'] == 4

    def test_add_number(self, context_defaults):
        context_defaults.add_number(7)
        assert context_defaults.data['number'] == 7

    def test_add(self, context_defaults, context_two):
        context_defaults.absorb(context_two)
        assert context_defaults.data == dict(foo='hotel', baz=5, qux=7)
