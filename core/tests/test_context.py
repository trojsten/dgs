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


class TestSchemaGuards:
    """
    `values`, `derived` and `eq` all name things, so they share one identifier rule, and a name may
    not silently replace something the context already holds.
    """

    @staticmethod
    def _meta(tmp_path, body: str):
        p = tmp_path / 'meta.yaml'
        p.write_text("authors: []\ntags: []\n" + body, encoding='utf-8')
        return p

    def test_duplicate_keys_are_refused(self, tmp_path):
        """PyYAML keeps the last value at the first key's position -- invisible, so refuse it."""
        from core.builder.context.context import DuplicateKeyError
        p = self._meta(tmp_path, "values:\n  a: 1\n  a: 2\n")
        with pytest.raises(DuplicateKeyError, match='a'):
            Context('x').load_yaml(p)

    def test_duplicate_keys_name_the_file(self, tmp_path):
        from core.builder.context.context import DuplicateKeyError
        p = self._meta(tmp_path, "eq:\n  foo: 'x'\n  foo: 'y'\n")
        with pytest.raises(DuplicateKeyError) as excinfo:
            Context('x').load_yaml(p)
        assert 'meta.yaml' in str(excinfo.value) and excinfo.value.keys == ['foo']

    def test_unique_keys_load_normally(self, tmp_path):
        p = self._meta(tmp_path, "values:\n  a: 1\n  b: 2\n")
        assert Context('x').load_yaml(p).data['values'] == {'a': 1, 'b': 2}

    @pytest.mark.parametrize("name", ['const', 'eq'])
    def test_reserved_names_are_refused(self, name):
        """The two names the render context holds itself; anything else spread in would clobber."""
        from core.builder.renderer import CLIInterface, NameCollisionError
        with pytest.raises(NameCollisionError, match=name):
            CLIInterface._reject_name_collisions({name: 'whatever'}, 'derived')

    @pytest.mark.parametrize("name", ['id', 'values', 'derived'])
    def test_only_real_context_names_are_reserved(self, name):
        """
        `values` and `derived` are section names in the file and `id` lives only in the metadata
        context -- none of them is a render-context name, so none of them is reserved.
        """
        from core.builder.renderer import CLIInterface
        CLIInterface._reject_name_collisions({name: '1'}, 'values')

    def test_a_value_may_share_a_name_with_a_constant(self):
        """`const` is adopted as a child context, so `const.g` and a value named `g` coexist."""
        from core.builder.renderer import CLIInterface
        CLIInterface._reject_name_collisions({'g': '1', 'c': '2', 'au': '3'}, 'values')

    def test_derived_may_not_shadow_a_value(self):
        from core.builder.renderer import CLIInterface, NameCollisionError
        with pytest.raises(NameCollisionError, match='already defined'):
            CLIInterface._reject_name_collisions({'v0': 'v0 * 2'}, 'derived', taken={'v0'})

    def test_ordinary_names_pass(self):
        from core.builder.renderer import CLIInterface
        CLIInterface._reject_name_collisions({'v0': '1', 'T_1': '2'}, 'derived', taken={'other'})

    def test_all_three_blocks_share_one_identifier_rule(self, tmp_path):
        """`eq` used to reject capitals and single-character names; the others never did."""
        from core.builder.renderer import StandaloneContext
        p = tmp_path / 'meta.yaml'
        p.write_text("values:\n  X: 1\nderived:\n  Y: 'X + 1'\neq:\n  v: 'v = 1'\n", encoding='utf-8')
        ctx = StandaloneContext('t', p).add(id='t')
        ctx.validate()          # must not raise
        assert set(ctx.data['eq']) == {'v'} and set(ctx.data['derived']) == {'Y'}
