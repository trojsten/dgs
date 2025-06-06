from pathlib import Path
from tempfile import SpooledTemporaryFile, NamedTemporaryFile

import pytest

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
        'a_lot': 123456789,
    }


class TestConstant:
    def test_does_it_render(self, temp_renderer, context_simple) -> None:
        x = NamedTemporaryFile(delete=False, delete_on_close=False)
        with open(x.name, 'w') as f:
            f.write('hello\n')
            f.close()

        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
        temp_renderer.render(x.name, context_simple, outfile=output)
        output.seek(0)

        assert output.readlines() == ['hello\n']

    def test_does_it_render_a_constant(self, renderer, context_simple) -> None:
        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
        renderer.render('constant.txt', context_simple, outfile=output)
        output.seek(0)
        assert output.readlines() == ['5\n']


#    def test_does_it_render_a_constant(self, renderer, context_simple) -> None:
#        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
#        renderer.render('constant.txt', context_simple, outfile=output)
#        output.seek(0)
#        assert output.readlines() == [r'\qty{}{}']


@pytest.fixture
def jinja_convertor(path):
    return JinjaConvertor(path)
    MarkdownJinjaRenderer(Path('core/tests/snippets'))


class TestJinjaConvertor:
    def test_does_it_render(self, temp_renderer, context_simple) -> None:
        output = NamedTemporaryFile('r+', delete=False, delete_on_close=False)
        renderer.render('constant.txt', context_simple, outfile=output)
        output.seek(0)
