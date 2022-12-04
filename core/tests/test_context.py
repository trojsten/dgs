import pytest
import math

from core.build.context import Context


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
    return Context(id=123, number=456)


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

    def test_add_id_override(self, context_defaults):
        context_defaults.add_id(555)
        assert context_defaults.data['id'] == 555

    def test_add_number_override(self, context_defaults):
        context_defaults.add_number(666)
        assert context_defaults.data['number'] == 666

    def test_add(self, context_defaults, context_two):
        context_defaults.absorb(context_two)
        assert context_defaults.data == dict(foo='hotel', baz=5, qux=7)
