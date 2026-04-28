import pytest

from core.builder.context.quantities.math import MathObject


@pytest.fixture
def inline():
    return MathObject('e1', 'a + b = c')


@pytest.fixture
def multiline():
    return MathObject('e2', 'a &= b + c \\\\\nb &= 2c')


class TestMathObjectInline:
    """Default formatting wraps content in $...$."""

    def test_str(self, inline):
        assert str(inline) == '$a + b = c$'

    def test_format_no_spec(self, inline):
        assert f'{inline}' == '$a + b = c$'

    def test_format_explicit_empty_spec(self, inline):
        assert format(inline, '') == '$a + b = c$'


class TestMathObjectDisplay:
    """`:disp` renders a numbered display equation with pandoc-crossref label."""

    def test_basic(self, inline):
        result = f'{inline:disp}'
        assert result.startswith('$$\n')
        assert '    a + b = c' in result  # 4-space indent
        assert result.endswith('{#eq:e1}')

    def test_label_uses_id(self):
        m = MathObject('mass-energy', 'E = mc^2')
        assert '{#eq:mass-energy}' in f'{m:disp}'

    def test_indents_each_line(self, multiline):
        result = f'{multiline:disp}'
        assert '    a &= b + c' in result
        assert '    b &= 2c' in result


class TestMathObjectAlign:
    """`:align` renders an aligned display equation."""

    def test_structure(self, multiline):
        result = f'{multiline:align}'
        assert result.startswith('$${\n')
        assert '\n}$$' in result
        assert result.endswith('{#eq:e2}')

    def test_indents_each_line(self, multiline):
        result = f'{multiline:align}'
        assert '    a &= b + c' in result
        assert '    b &= 2c' in result


class TestMathObjectInterpunction:
    """
    A trailing punctuation character in the spec is appended to the math
    content, so the equation can end a sentence cleanly.
    """

    @pytest.mark.parametrize("punct", list('.,;?!'))
    def test_inline_with_punctuation(self, inline, punct):
        assert f'{inline:{punct}}' == f'$a + b = c{punct}$'

    @pytest.mark.parametrize("punct", list('.,;?!'))
    def test_disp_with_punctuation(self, inline, punct):
        result = f'{inline:disp{punct}}'
        # Punctuation lands at end of math content, before the closing $$.
        assert f'a + b = c{punct}\n$$' in result

    @pytest.mark.parametrize("punct", list('.,;?!'))
    def test_align_with_punctuation(self, multiline, punct):
        result = f'{multiline:align{punct}}'
        # Punctuation lands after the last content line, before `\n}$$`.
        assert f'b &= 2c{punct}\n}}$$' in result

    def test_punctuation_only_spec_treated_as_inline(self, inline):
        """`:.` strips the period and falls through to the empty-spec branch."""
        assert f'{inline:.}' == '$a + b = c.$'

    def test_non_punctuation_char_not_stripped(self, inline):
        """A trailing letter is not interpunction; the spec is rejected."""
        with pytest.raises(NotImplementedError):
            f'{inline:dispx}'


class TestMathObjectErrors:
    def test_unknown_spec(self, inline):
        with pytest.raises(NotImplementedError, match="foo"):
            f'{inline:foo}'

    def test_unknown_spec_with_punctuation(self, inline):
        """Unknown specs with valid punctuation suffix still raise on the prefix."""
        with pytest.raises(NotImplementedError, match="foo"):
            f'{inline:foo.}'


class TestMathObjectConstruction:
    def test_strips_trailing_newline(self):
        """Constructor strips a single trailing newline from content."""
        m = MathObject('e', 'a + b\n')
        assert m.content == 'a + b'

    def test_preserves_internal_newlines(self):
        m = MathObject('e', 'a\nb\nc')
        assert m.content == 'a\nb\nc'

    def test_repr(self, inline):
        assert repr(inline) == "'$a + b = c$'"