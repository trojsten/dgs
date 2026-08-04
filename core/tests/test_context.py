import pytest

from core.builder.context import Context
from core.builder.jinja import MarkdownJinjaRenderer, MissingVariablesError


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
        assert context_override.data == {'fks': {'boss': 'Marcel', 'pictures': 'KatkaN', 'htr': 'Kvík', 'nothing': 'Nina'}}

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
        assert context_defaults.data == {'foo': 'hotel', 'baz': 5, 'qux': 7}

    def test_ior(self):
        first = Context('fks', boss='Matúš', coffee='Nina')
        second = Context('htr', pictures='KatkaN', htr='Kvík', iy='Krto')
        assert first | second == Context('fks', boss='Matúš', coffee='Nina', pictures='KatkaN', htr='Kvík', iy='Krto')

    def test_or(self):
        """ Note that or'ed contexts retain the parent's name but override items with child's """
        assert Context('foo', bar='mitzvah') | Context('baz', bar='baron') == Context('foo', bar='baron')


class TestMissingVariables:
    def test_single_missing_raises(self):
        r = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError) as exc:
            r.render('(§ name §)', {})
        assert exc.value.missing == ['name']

    def test_multiple_missing_collected(self):
        r = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError) as exc:
            r.render('(§ a §) and (§ b §) and (§ c §)', {})
        assert exc.value.missing == ['a', 'b', 'c']

    def test_all_present_succeeds(self):
        r = MarkdownJinjaRenderer()
        assert r.render('(§ x §)', {'x': 42}) == '42'

    def test_registry_clears_between_renders(self):
        r = MarkdownJinjaRenderer()
        try:
            r.render('(§ missing §)', {})
        except MissingVariablesError:
            pass
        # Next render with all defined should succeed
        assert r.render('(§ x §)', {'x': 1}) == '1'

class TestEvaluate:
    """
    `MarkdownJinjaRenderer.evaluate` returns the *object* a Jinja expression produces, not its
    rendering. This is what `derived:` entries in a problem's metadata are built on.
    """

    @pytest.fixture
    def renderer(self):
        return MarkdownJinjaRenderer()

    def test_returns_an_object_not_a_string(self, renderer):
        from core.builder.context.quantities import PhysicsQuantity
        value = renderer.evaluate("PQ(3, 'metre')", {})
        assert isinstance(value, PhysicsQuantity)
        assert value.mag == 3

    def test_globals_and_filters_are_available(self, renderer):
        assert renderer.evaluate("sqrt(PQ(4, 'm^2'))", {}).mag == 2
        assert renderer.evaluate("pi", {}) == pytest.approx(3.14159, abs=1e-4)

    def test_context_names_are_visible(self, renderer):
        assert renderer.evaluate("a + b", {'a': 2, 'b': 5}) == 7

    def test_quantities_compose(self, renderer):
        """The point of `derived:`: later entries build on earlier ones."""
        from core.builder.context.quantities import PhysicsQuantity
        v = renderer.evaluate("s / t", {'s': PhysicsQuantity.construct(100, 'm'),
                                        't': PhysicsQuantity.construct(4, 's')})
        assert f'{v:g}' == r'\qty{25}{\meter\per\second}'

    def test_unknown_name_raises(self, renderer):
        """A typo must not silently evaluate to an empty string, as bare rendering would."""
        with pytest.raises(MissingVariablesError):
            renderer.evaluate("nonexistent_variable", {})

    def test_unknown_name_in_arithmetic_raises(self, renderer):
        with pytest.raises(MissingVariablesError):
            renderer.evaluate("2 * nonexistent_variable", {'a': 1})

    def test_missing_name_is_reported(self, renderer):
        with pytest.raises(MissingVariablesError, match='nonexistent_variable'):
            renderer.evaluate("nonexistent_variable", {})
