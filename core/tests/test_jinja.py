from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import regex as re

from core.builder.context import PhysicsConstant
from core.builder.jinja import MarkdownJinjaRenderer
from jinja import JinjaConvertor, CLIInterface

from pint import UnitRegistry as u


@pytest.fixture
def temp_renderer():
    return MarkdownJinjaRenderer(Path('/'))


@pytest.fixture
def renderer():
    return MarkdownJinjaRenderer(Path('core/tests/snippets'))


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


def render_to_temporary(file, renderer, context) -> list[str]:
    output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
    renderer.render(file.name, context, outfile=output)
    output.seek(0)
    return output.readlines()


def render_string_to_temporary(string, renderer, context) -> list[str]:
    output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
    renderer.render(string, context, outfile=output)
    output.seek(0)
    return output.readlines()


class TestConstant:
    @pytest.mark.parametrize("source,result", [
        pytest.param('hello', 'hello', id='hello'),
        pytest.param(r'(§ large §) < (§ giga|g §)', r'123456789 < e\+?09\n', id='complex'),
        pytest.param('(§ your_mom|g5 §)', r'3.14e\+?15\n?', id='sci5'),
        pytest.param('(§ small|g4 §)', r'2.443e-19\n?', id='sci-small'),
        pytest.param('(§ (small * your_mom * five**5)|g5 §)', r'2.3975\n?', id='complex-expression'),
        pytest.param('(§ cos(1)|float(5) §)', r'0.54030\n?', id='cos(1)'),
        pytest.param('(§ cos(1)|nf5 §)', r'\\num{0.54030}\n?', id='cos(1) num'),
    ])
    def test_render(self, source, result, temp_renderer, context_simple) -> None:
        ntf = create_temporary_file(source)
        rr = re.compile(result)
        output = render_to_temporary(ntf, temp_renderer, context_simple)[0]
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
    def test_does_it_render(self, source, expected, renderer, context_simple) -> None:
        result = render_string_to_temporary(source, renderer, context_simple)
        assert result == [f"{expected}\n"], \
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
        pytest.param('g', r'\\(SI|qty)(\[\])?{9.80665}{\\met(re|er)\\per\\second\\squared}', id='g'),
        #pytest.param('c', r'\\(SI|qty){299792458}{\\metre\\per\\second}', id='c'),
        pytest.param('G', r'\\(SI|qty)(\[\])?{6.6743e-11}{\\newton\\per\\kilo\\gram\\squared\\per\\met(re|er)\\squared}', id='G'),
    ])
    def test_full_value(self, name, expected, context_constants):
        value = f"{context_constants[name]}"
        assert re.compile(expected).match(value), f"Got {value}"

#    def test_does_it_render_a_constant(self, renderer, context_simple) -> None:
#        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
#        renderer.render('constant.txt', context_simple, outfile=output)
#        output.seek(0)
#        assert output.readlines() == [r'\qty{}{}']


@pytest.fixture
def cli():
    return CLIInterface(locale='sk')


class TestJinjaCLI:
    def disable_test_constants(self, cli):
        cli.run()
