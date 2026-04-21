from pathlib import Path
from tempfile import NamedTemporaryFile, SpooledTemporaryFile

import pytest
import regex as re

from core.builder.context import PhysicsConstant
from core.builder.jinja import MarkdownJinjaRenderer, MissingVariablesError

from pint import UnitRegistry as u


@pytest.fixture
def context_simple():
    return {
        'five': 5,
        'e': 2.718281828,
        'large': 123456789,
        'giga': 1e9,
        'your_mom': 3.14e15,
        'small': 2.4433e-19,
    }

@pytest.fixture
def context_constants():
    return {
        'c': PhysicsConstant('speed_of_light', u.Quantity(299792458, 'metre / second'), digits=3),
        'g': PhysicsConstant('gforce', u.Quantity(9.80665, 'metre / second^2'), digits=1),
        'G': PhysicsConstant('gravity', u.Quantity(6.67430e-11, 'newton / metre squared / kilogram squared'), digits=4),
    }

def create_temporary_file(string):
    """
    Create a named temporary file with string content for use in tests
    """
    ntf = NamedTemporaryFile('w+')
    with open(ntf.name, 'w') as file:
        file.write(string)
        file.close()

    return ntf


def render_string_to_temporary(string, context) -> str:
    renderer = MarkdownJinjaRenderer()
    return renderer.render(string, context)


def render_file_to_temporary(source, context) -> str:
    renderer = MarkdownJinjaRenderer()
    with open(source, 'r' ) as file:
        return renderer.render(file.read(), context)


class TestConstant:
    @pytest.mark.parametrize("template,expected", [
        pytest.param('hello', 'hello', id='hello'),
        pytest.param(r'(§ large §) < (§ giga|g §)', r'123456789 < e\+?09', id='complex'),
        pytest.param('(§ your_mom|g5 §)', r'3.14e\+?15\n?', id='sci5'),
        pytest.param('(§ small|g4 §)', r'2.443e-19\n?', id='sci-small'),
        pytest.param('(§ (small * your_mom * five**5)|g5 §)', r'2.3975\n?', id='complex-expression'),
        pytest.param('(§ cos(1)|float(5) §)', r'0.54030\n?', id='cos(1)'),
        pytest.param('(§ cos(1)|nf5 §)', r'\\num{0.54030}\n?', id='cos(1) num'),
    ])
    def test_render(self, template, expected, context_simple) -> None:
        rr = re.compile(expected)
        output = render_string_to_temporary(template, context_simple)
        assert rr.match(output), output

    @pytest.mark.parametrize("source,expected", [
        pytest.param('e/f3.txt', '2.718', id='e-f3'),
        pytest.param('e/f6.txt', '2.718282', id='e-f6'),
        pytest.param('e/g3.txt', '2.72', id='e-g3'),
        pytest.param('e/g6.txt', '2.71828', id='e-g6'),
        pytest.param('large/f3.txt', '123456789.000', id='large-f3'),
        pytest.param('large/f0.txt', '123456789', id='large-f0'),
        pytest.param('large/g3.txt', '1.23e+08', id='large-f0'),
        pytest.param('simplest.txt', 'hello', id='hello'),

        pytest.param('constant.txt', '5'),
        pytest.param('big_one.txt', '1.23e+08'),
        pytest.param('big_one_num.txt', r'\num{1.23e+08}'),
        pytest.param('giga.txt', 'e+09'),
    ])
    def test_does_it_render(self, source, expected, context_simple) -> None:
        result = render_file_to_temporary(Path('core/tests') / 'snippets' / source, context_simple)
        assert result == expected, \
            f"Expected {expected}, got {result}"

    @pytest.mark.parametrize("name,expected,digits", [
        pytest.param('g', u.Quantity(10.0, 'meter / second^2'), 1, id='g'),
        pytest.param('c', u.Quantity(3e8, 'meter / second'), 1, id='c'),
        pytest.param('G', u.Quantity(6.674e-11, 'newton / kilogram^2 / meter^2'), 4, id='G'),
    ])
    def test_approximation(self, name, expected, digits, context_constants):
        value = context_constants[name].approximate(digits)
        assert value._quantity == expected, f"Expected {expected}, got {value}"

    @pytest.mark.parametrize("name,expected", [
        pytest.param('g', r'\\(SI|qty)\{9.80665\}{\\met(re|er)\\per\\second\\squared}$', id='g'),
        pytest.param('G', r'\\(SI|qty){6.6743e-11}{\\newton\\per\\kilo\\gram\\squared\\per\\met(re|er)\\squared}$', id='G'),
        pytest.param('c', r'\\(SI|qty)\{299792458\}{\\met(re|er)\\per\\second}$', id='c'),
    ])
    def test_full_value(self, name, expected, context_constants):
        value = f"{context_constants[name]}"
        assert re.compile(expected).match(value), f"Got {value}"

#    def test_does_it_render_a_constant(self, renderer, context_simple) -> None:
#        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
#        renderer.render('constant.txt', context_simple, outfile=output)
#        output.seek(0)
#        assert output.readlines() == [r'\qty{}{}']


class TestMissingVariables:
    """
    Option B: missing variables do not abort rendering; they are collected
    across the whole pass and raised together at the end.
    """

    def test_single_missing_raises(self):
        renderer = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError) as exc:
            renderer.render('(§ name §)', {})
        assert exc.value.missing == ['name']

    def test_multiple_missing_collected(self):
        renderer = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError) as exc:
            renderer.render('(§ a §) and (§ b §) and (§ c §)', {})
        assert exc.value.missing == ['a', 'b', 'c']

    def test_duplicate_references_deduped(self):
        renderer = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError) as exc:
            renderer.render('(§ x §) (§ x §) (§ y §)', {})
        assert exc.value.missing == ['x', 'y']

    def test_all_present_succeeds(self):
        renderer = MarkdownJinjaRenderer()
        assert renderer.render('(§ x §)', {'x': 42}) == '42'

    def test_registry_clears_between_renders(self):
        renderer = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError):
            renderer.render('(§ missing §)', {})
        # Stale names must not leak into the next render.
        assert renderer.render('(§ x §)', {'x': 1}) == '1'

    def test_renderers_have_isolated_registries(self):
        r1 = MarkdownJinjaRenderer()
        r2 = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError):
            r1.render('(§ a §)', {})
        # r2's registry must not contain r1's misses.
        with pytest.raises(MissingVariablesError) as exc:
            r2.render('(§ b §)', {})
        assert exc.value.missing == ['b']

    def test_default_filter_suppresses_miss(self):
        """
        `x | default(value)` should treat x as optional: when x is missing,
        the fallback is substituted and the name is NOT reported as a miss.
        """
        renderer = MarkdownJinjaRenderer()
        assert renderer.render('(§ x|default("fallback") §)', {}) == 'fallback'

    def test_default_filter_mixed_with_real_miss(self):
        """
        A template with both a defaulted-optional and a genuinely required
        variable should raise only for the required one.
        """
        renderer = MarkdownJinjaRenderer()
        with pytest.raises(MissingVariablesError) as exc:
            renderer.render('(§ a|default("") §) (§ b §)', {})
        assert exc.value.missing == ['b']
