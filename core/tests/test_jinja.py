from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import regex as re

from core.builder.jinja import MarkdownJinjaRenderer
from jinja import JinjaConvertor, CLIInterface


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

def create_temporary_file(string):
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
        pytest.param(r'(§ large §) < (§ giga|sci §)', r'123456789 < e\+?09\n', id='complex'),
        pytest.param('(§ your_mom|sci(5) §)', r'3.14e\+?15\n?', id='sci5'),
        pytest.param('(§ small|sci(4) §)', r'2.443e-19\n?', id='sci-small'),
        pytest.param('(§ (small * your_mom * five**5)|sci(5) §)', r'2.3975\n?', id='complex-expression'),
        pytest.param('(§ cos(1)|float(5) §)', r'0.54030\n?', id='cos(1)'),
        pytest.param('(§ cos(1)|num(5) §)', r'\\num{0.5403}\n?', id='cos(1) num'),
    ])
    def test_render(self, source, result, temp_renderer, context_simple) -> None:
        ntf = create_temporary_file(source)
        rr = re.compile(result)
        output = render_to_temporary(ntf, temp_renderer, context_simple)[0]
        assert rr.match(output), output


    def test_does_it_render_anything(self, renderer, context_simple) -> None:
        assert render_string_to_temporary('simplest.txt', renderer, context_simple) == ['hello\n']

    def test_does_it_render_a_constant(self, renderer, context_simple) -> None:
        assert render_string_to_temporary('constant.txt', renderer, context_simple) == ['5\n']

    def test_does_it_render_a_float(self, renderer, context_simple) -> None:
        assert render_string_to_temporary('float.txt', renderer, context_simple) == ['2.718\n']

    def test_does_it_render_a_big_one(self, renderer, context_simple) -> None:
        assert render_string_to_temporary('big_one.txt', renderer, context_simple) == ['1.23e+08\n']

    def test_does_it_render_a_big_one_num(self, renderer, context_simple) -> None:
        assert render_string_to_temporary('big_one_num.txt', renderer, context_simple) == ['\\num{1.23e+08}\n']

    def test_does_it_render_a_huge_one(self, renderer, context_simple) -> None:
        assert render_string_to_temporary('giga.txt', renderer, context_simple) == ['e+09\n']


#    def test_does_it_render_a_constant(self, renderer, context_simple) -> None:
#        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
#        renderer.render('constant.txt', context_simple, outfile=output)
#        output.seek(0)
#        assert output.readlines() == [r'\qty{}{}']


@pytest.fixture
def jinja_convertor(path):
    return JinjaConvertor(path)
    MarkdownJinjaRenderer(Path('core/tests/snippets'))


# ToDo this is just copied from above
class TestJinjaConvertor:
    def test_does_it_render(self, renderer, context_simple) -> None:
        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
        renderer.render('constant.txt', context_simple, outfile=output)
        output.seek(0)

        assert output.readlines() == ['5\n']