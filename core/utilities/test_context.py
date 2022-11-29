import pytest
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

    def test_split_callback_bad_count(self):
        with pytest.raises(IndexError):
            split_callback(list(range(0, 12)), is_prime, 1)


@pytest.fixture
def context_empty():
    return Context()

@pytest.fixture
def context_defaults():
    return Context(defaults={
        'foo': 'bar',
        'baz': 5,
    })

@pytest.fixture
def context_old():
    return Context(defaults=dict(boss='Dušan', pictures='Plyš', htr='Kvík'))

@pytest.fixture
def context_new():
    return Context(defaults=dict(boss='Marcel', pictures='Terka', nothing='Nina'))

@pytest.fixture
def context_override(context_old, context_new):
    ctx = Context()
    print(ctx.data)
    ctx.adopt('fks', context_old)
    ctx.adopt('fks', context_new)
    return ctx


class TestContext():
    def test_empty(self, context_empty):
        assert context_empty.data == {}

    def test_empty_nothing(self, context_defaults):
        with pytest.raises(KeyError):
            context_defaults.data['boo']

    def test_default(self, context_defaults):
        assert context_defaults.data == {'foo': 'bar', 'baz': 5}

    def test_add_id(self, context_defaults):
        context_defaults.add_id(4)
        assert context_defaults.data['id'] == 4

    def test_adopt_override(self, context_override):
        assert context_override.data['fks']['pictures'] == 'Terka'

    def test_adopt_notoverride(self, context_override):
        assert context_override.data['fks']['htr'] == 'Kvík'

    def test_adopt_new(self, context_override):
        assert context_override.data['fks']['nothing'] == 'Nina'
