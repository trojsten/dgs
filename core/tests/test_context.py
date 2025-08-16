import pytest

from core.builder.context import Context


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
    return Context(boss='Marcel', pictures='KatkaN', nothing='Nina')


@pytest.fixture
def context_override(context_empty, context_old, context_new):
    context_empty.adopt(fks=context_old)
    context_empty.adopt(fks=context_new)
    return context_empty


@pytest.fixture
def context_numbered():
    return Context(id=123, number=456)


class TestContext:
    def test_empty(self, context_empty):
        assert context_empty.data == {}

    def test_empty_nothing(self, context_defaults):
        with pytest.raises(KeyError):
            _ = context_defaults.data['boo']

    def test_default(self, context_defaults):
        assert context_defaults.data == {'foo': 'bar', 'baz': 5}

    def test_adopt_override(self, context_override):
        assert context_override.data['fks']['pictures'] == 'KatkaN'

    def test_adopt_no_override(self, context_override):
        assert context_override.data['fks']['htr'] == 'Kvík'

    def test_adopt_new(self, context_override):
        assert context_override.data['fks']['nothing'] == 'Nina'

    def test_adopt_full(self, context_override):
        assert context_override.data == dict(fks=dict(boss='Marcel', pictures='KatkaN', htr='Kvík', nothing='Nina'))

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
        context_defaults |= context_two
        assert context_defaults.data == dict(foo='hotel', baz=5, qux=7)

    def test_ior(self):
        first = Context('fks', boss='Matúš', coffee='Nina')
        second = Context('htr', pictures='KatkaN', htr='Kvík', iy='Krto')
        assert first | second == Context('fks', boss='Matúš', coffee='Nina', pictures='KatkaN', htr='Kvík', iy='Krto')

    def test_or(self):
        """ Note that or'ed contexts retain the parent's name but override items with child's """
        assert Context('foo', bar='mitzvah') | Context('baz', bar='baron') == Context('foo', bar='baron')