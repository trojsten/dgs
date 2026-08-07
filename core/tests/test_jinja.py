from pathlib import Path
from tempfile import NamedTemporaryFile

import jinja2
import pytest
import regex as re
from pint import UnitRegistry as u

from core.builder.context import PhysicsConstant
from core.builder.jinja import MarkdownJinjaRenderer, MissingVariablesError


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


class TestMathFilters:
    """
    The inline/disp/align filters delegate to MathObject.__format__.
    disp and align accept an optional punctuation argument; inline does not.
    """

    @pytest.fixture
    def renderer(self):
        return MarkdownJinjaRenderer()

    @pytest.fixture
    def context(self):
        from core.builder.context.quantities.math import MathObject
        return {
            'eq': MathObject('e1', 'a + b = c'),
            'multi': MathObject('e2', 'a &= b + c \\\\\nb &= 2c'),
        }

    def test_bare_reference_is_raw(self, renderer, context):
        """No filter means no delimiters: the fragment, for building a larger expression."""
        assert renderer.render('(§ eq §)', context) == 'a + b = c'

    def test_raw_filter_matches_bare(self, renderer, context):
        assert renderer.render('(§ eq | raw §)', context) == 'a + b = c'

    def test_inl(self, renderer, context):
        assert renderer.render('(§ eq | inl §)', context) == '$a + b = c$'

    def test_inl_does_not_accept_punctuation(self, renderer, context):
        """The inline filter takes no arguments; punctuation goes outside."""
        with pytest.raises(TypeError):
            renderer.render('(§ eq | inl(".") §)', context)

    def test_disp_no_arg(self, renderer, context):
        result = renderer.render('(§ eq | disp §)', context)
        assert '    a + b = c\n$$' in result
        assert '{#eq:e1}' in result

    def test_disp_with_comma(self, renderer, context):
        result = renderer.render('(§ eq | disp(",") §)', context)
        assert '    a + b = c,\n$$' in result

    def test_align_no_arg(self, renderer, context):
        result = renderer.render('(§ multi | align §)', context)
        assert '    b &= 2c\n}$$' in result

    def test_align_with_period(self, renderer, context):
        result = renderer.render('(§ multi | align(".") §)', context)
        assert '    b &= 2c.\n}$$' in result

    def test_invalid_punctuation_rejected(self, renderer, context):
        """An unsupported punctuation char is reported with a friendly message."""
        with pytest.raises(ValueError, match="Invalid trailing character 'x'"):
            renderer.render('(§ eq | disp("x") §)', context)


DISP_SHORTHANDS = [
    pytest.param('dispd', '.', id='dispd'),
    pytest.param('dispc', ',', id='dispc'),
    pytest.param('disps', ';', id='disps'),
    pytest.param('dispq', '?', id='dispq'),
    pytest.param('dispe', '!', id='dispe'),
]

ALIGN_SHORTHANDS = [
    pytest.param('alignd', '.', id='alignd'),
    pytest.param('alignc', ',', id='alignc'),
    pytest.param('aligns', ';', id='aligns'),
    pytest.param('alignq', '?', id='alignq'),
    pytest.param('aligne', '!', id='aligne'),
]


class TestMathPunctuationShorthands:
    """
    `dispd`/`dispc`/`disps`/`dispq`/`dispe` and the matching `align*` filters are
    functools.partial shorthands binding the trailing punctuation (dot / comma /
    semicolon / question mark / exclamation mark), so that `| dispd` means exactly
    `| disp('.')`. Together they cover all of `MathObject._INTERPUNCTION`.
    """

    @pytest.fixture
    def renderer(self):
        return MarkdownJinjaRenderer()

    @pytest.fixture
    def context(self):
        from core.builder.context.quantities.math import MathObject
        return {
            'eq': MathObject('e1', 'a + b = c'),
            'multi': MathObject('e2', 'a &= b + c \\\\\nb &= 2c'),
        }

    @pytest.mark.parametrize("shorthand,punct", DISP_SHORTHANDS)
    def test_disp_shorthand(self, renderer, context, shorthand, punct):
        assert renderer.render(f'(§ eq | {shorthand} §)', context) == \
               f'$$\n    a + b = c{punct}\n$$ {{#eq:e1}}'

    @pytest.mark.parametrize("shorthand,punct", ALIGN_SHORTHANDS)
    def test_align_shorthand(self, renderer, context, shorthand, punct):
        assert renderer.render(f'(§ multi | {shorthand} §)', context) == \
               f'$${{\n    a &= b + c \\\\\n    b &= 2c{punct}\n}}$$ {{#eq:e2}}'

    @pytest.mark.parametrize("shorthand,punct", DISP_SHORTHANDS)
    def test_disp_shorthand_matches_explicit(self, renderer, context, shorthand, punct):
        """The whole point of the shorthand: identical output to the explicit call."""
        assert renderer.render(f'(§ eq | {shorthand} §)', context) == \
               renderer.render(f'(§ eq | disp("{punct}") §)', context)

    @pytest.mark.parametrize("shorthand,punct", ALIGN_SHORTHANDS)
    def test_align_shorthand_matches_explicit(self, renderer, context, shorthand, punct):
        assert renderer.render(f'(§ multi | {shorthand} §)', context) == \
               renderer.render(f'(§ multi | align("{punct}") §)', context)

    def test_shorthands_are_distinct(self, renderer, context):
        """Guards against copy-paste: each shorthand must bind its own punctuation."""
        disp_names = [p.values[0] for p in DISP_SHORTHANDS]
        align_names = [p.values[0] for p in ALIGN_SHORTHANDS]
        disp = {s: renderer.render(f'(§ eq | {s} §)', context) for s in disp_names}
        align = {s: renderer.render(f'(§ multi | {s} §)', context) for s in align_names}
        assert len(set(disp.values())) == len(disp_names), disp
        assert len(set(align.values())) == len(align_names), align

    def test_shorthands_cover_all_interpunction(self):
        """Every punctuation mark `MathObject` accepts must have a shorthand."""
        from core.builder.context.quantities.math import MathObject
        for names, params in (('disp', DISP_SHORTHANDS), ('align', ALIGN_SHORTHANDS)):
            bound = {p.values[1] for p in params}
            assert bound == set(MathObject._INTERPUNCTION), (names, bound)

    def test_disp_shorthand_is_not_align(self, renderer, context):
        """`disp*` must not be wired to math_aligned (or vice versa)."""
        assert renderer.render('(§ eq | dispd §)', context).startswith('$$\n')
        assert renderer.render('(§ multi | alignd §)', context).startswith('$${\n')

    @pytest.mark.parametrize("shorthand", [p.values[0] for p in DISP_SHORTHANDS + ALIGN_SHORTHANDS])
    def test_shorthand_takes_no_argument(self, renderer, context, shorthand):
        """Punctuation is already bound, so passing another one is a conflict."""
        with pytest.raises(TypeError):
            renderer.render(f'(§ eq | {shorthand}(".") §)', context)


class TestApproxEqualsFilters:
    """
    `ef`/`eg` render `symbol = value`; `af`/`ag` render `symbol \\approx value`.
    All four exist bare (Python's default formatting for the kind) and suffixed 0-9
    for an explicit precision.
    """

    @pytest.fixture
    def renderer(self):
        return MarkdownJinjaRenderer()

    @pytest.fixture
    def context(self):
        from core.builder.context.quantities import PhysicsQuantity
        return {'m': PhysicsQuantity.construct(96.7, 'kg', symbol='m_D')}

    def test_ef0(self, renderer, context):
        assert renderer.render('(§ m | ef0 §)', context) == r'm_D = \qty{97}{\kilo\gram}'

    def test_eg2(self, renderer, context):
        assert renderer.render('(§ m | eg2 §)', context) == r'm_D = \qty{97}{\kilo\gram}'

    def test_af0(self, renderer, context):
        assert renderer.render('(§ m | af0 §)', context) == r'm_D \approx \qty{97}{\kilo\gram}'

    def test_ag2(self, renderer, context):
        assert renderer.render('(§ m | ag2 §)', context) == r'm_D \approx \qty{97}{\kilo\gram}'

    def test_af2(self, renderer, context):
        assert renderer.render('(§ m | af2 §)', context) == r'm_D \approx \qty{96.70}{\kilo\gram}'

    def test_ef_bare(self, renderer, context):
        """No precision means Python's default 'f', i.e. six decimals — same as `| f`."""
        assert renderer.render('(§ m | ef §)', context) == r'm_D = \qty{96.700000}{\kilo\gram}'

    def test_eg_bare(self, renderer, context):
        assert renderer.render('(§ m | eg §)', context) == r'm_D = \qty{96.7}{\kilo\gram}'

    def test_af_bare(self, renderer, context):
        assert renderer.render('(§ m | af §)', context) == r'm_D \approx \qty{96.700000}{\kilo\gram}'

    def test_ag_bare(self, renderer, context):
        assert renderer.render('(§ m | ag §)', context) == r'm_D \approx \qty{96.7}{\kilo\gram}'

    @pytest.mark.parametrize("equals,approx", [
        pytest.param('ef', 'af', id='float'),
        pytest.param('eg', 'ag', id='general'),
    ])
    def test_bare_approx_matches_bare_equals(self, renderer, context, equals, approx):
        """The bare forms may only differ in the relation symbol."""
        assert renderer.render(f'(§ m | {approx} §)', context).replace(r'\approx', '=') == \
               renderer.render(f'(§ m | {equals} §)', context)

    @pytest.mark.parametrize("bare,suffixed", [
        pytest.param('ag', 'ag6', id='eg'),
        pytest.param('af', 'af6', id='ef'),
    ])
    def test_bare_matches_default_precision(self, renderer, context, bare, suffixed):
        """Python's default for both 'f' and 'g' is six digits, so these coincide here."""
        assert renderer.render(f'(§ m | {bare} §)', context) == \
               renderer.render(f'(§ m | {suffixed} §)', context)


class TestQuantityConstructorGlobals:
    """
    The ad-hoc constructor is `PQ`, not `Q`: `Q` is heat/charge in half the
    problems, so a `@J set Q = ...` shadowing the constructor was too easy.
    """

    @pytest.fixture
    def renderer(self):
        return MarkdownJinjaRenderer()

    def test_pq_constructs_a_quantity(self, renderer):
        assert renderer.render("(§ PQ(96.7, 'kg') | f2 §)", {}) == r'\qty{96.70}{\kilo\gram}'

    def test_pq_is_usable_in_arithmetic(self, renderer):
        assert renderer.render("(§ (PQ(2, 'm') * PQ(3, 'm')) | f0 §)", {}) == r'\qty{6}{\meter\squared}'

    def test_bare_q_is_not_a_global(self, renderer):
        """
        The old name must be gone, not silently aliased. Calling an undefined
        raises `UndefinedError` straight away (jinja2 binds `Undefined.__call__`
        before `CollectUndefined` can intercept it), so this never reaches the
        collected-variables check.
        """
        with pytest.raises((jinja2.UndefinedError, MissingVariablesError)):
            renderer.render("(§ Q(96.7, 'kg') | f2 §)", {})

    def test_q_is_free_for_authors(self, renderer):
        """A context variable named `Q` (heat, charge) no longer collides."""
        from core.builder.context.quantities import PhysicsQuantity
        heat = PhysicsQuantity.construct(2.2e6, 'J', symbol='Q')
        assert renderer.render('(§ Q | eg2 §)', {'Q': heat}) == r'Q = \qty{2.2e+06}{\joule}'

    @pytest.mark.parametrize("alias,long", [
        pytest.param('QL', 'QuantityList', id='list'),
        pytest.param('QP', 'QuantityProduct', id='product'),
        pytest.param('QR', 'QuantityRange', id='range'),
    ])
    def test_other_constructors_keep_both_names(self, renderer, alias, long):
        """Only `Q` was renamed; the QL/QP/QR pairs are untouched."""
        args = "PQ(1, 'm'), PQ(2, 'm')"
        assert renderer.render(f'(§ {alias}({args}) | f0 §)', {}) == \
               renderer.render(f'(§ {long}({args}) | f0 §)', {})


class TestEqualsFiltersWithoutSymbol:
    """A symbol-less quantity must crash the render, not emit `None = ...`."""

    @pytest.fixture
    def renderer(self):
        return MarkdownJinjaRenderer()

    @pytest.mark.parametrize("filt", ['ef', 'ef2', 'eg', 'eg2', 'af', 'af2', 'ag', 'ag2'])
    def test_symbol_less_render_raises(self, renderer, filt):
        from core.builder.context.quantities import MissingSymbolError
        with pytest.raises(MissingSymbolError):
            renderer.render(f"(§ PQ(11.345, 'm/s^2') | {filt} §)", {})
