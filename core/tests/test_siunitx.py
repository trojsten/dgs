"""
siunitx expanded into ordinary TeX, which is what the web gets instead of siunitx itself.

The reason this exists rather than a pile of MathJax macros is the thing worth testing: a macro
substitutes, and three of these forms need the argument *parsed*. A list is several values, an
angle in `d;m;s` form is three, and an exponent is a mantissa and a power. Each of those has a
test here, because each is what a macro shim silently got wrong.

The other half is that the page has to agree with the booklet. The separators come from
`core/latex/siunitx.tex`'s own `\\sisetup` and the decimal marker and list words from the locale,
so Slovak writes `83{,}5` and `1 m, 2 m a 3 m` while English writes `83.5` and `and`.
"""
import pytest

from core.filters import siunitx
from core.filters.siunitx import expand, format_number, format_unit, symbol
from core.i18n import languages


@pytest.fixture(scope='module')
def sk():
    return languages['sk']


@pytest.fixture(scope='module')
def en():
    return languages['en']


class TestTheFormsAMacroCannotDo:
    """The three that justify a parser. Each was wrong under macro substitution."""

    def test_a_list_becomes_its_values(self, sk):
        """`\\qtylist{1;2;3}{\\metre}` is three quantities, not the string `1;2;3`."""
        assert expand(r'\qtylist{1;2;3}{\metre}', sk) == r'1\ \text{m,}\ 2\ \text{m a }3\ \text{m}'

    def test_an_angle_in_parts_becomes_degrees_minutes_seconds(self, sk):
        assert expand(r'\ang{44;9;}', sk) == r'44^\circ\,9^\prime'

    def test_an_exponent_becomes_a_power_of_ten(self, sk):
        assert expand(r'\num{1.0e+15}', sk) == r'1{,}0\cdot10^{15}'

    def test_an_empty_mantissa_has_no_stray_product(self, sk):
        """`cut_extra_one` writes `e+15` so siunitx sets a bare power; nothing may precede it."""
        assert expand(r'\num{e+15}', sk) == r'10^{15}'


class TestItAgreesWithTheBooklet:
    """Settings are read off `\\sisetup` and the locale, never chosen here."""

    def test_the_decimal_marker_follows_the_language(self, sk, en):
        assert format_number('83.5', sk) == '83{,}5'
        assert format_number('83.5', en) == '83.5'

    def test_a_comma_is_wrapped_and_a_full_stop_is_not(self, sk, en):
        """A bare comma in maths is punctuation and would take punctuation spacing."""
        assert '{,}' in format_number('1.5', sk)
        assert '{' not in format_number('1.5', en)

    def test_the_list_word_follows_the_language(self, sk, en):
        assert expand(r'\qtylist{1;2}{\metre}', sk) == r'1\ \text{m a }2\ \text{m}'
        assert expand(r'\qtylist{1;2}{\metre}', en) == r'1\ \text{m and }2\ \text{m}'

    def test_grouping_starts_at_five_digits(self, en):
        """`group-minimum-digits = 5`, so four digits stay bare."""
        assert format_number('1234', en) == '1234'
        assert format_number('12345', en) == r'12\,345'

    def test_per_is_a_solidus_because_per_mode_is_symbol(self, sk):
        assert format_unit(r'\metre\per\second', sk) == r'\text{m}/\text{s}'

    def test_a_prefix_abuts_its_unit(self, sk):
        """`inter-unit-product` is empty, so `\\kilo\\gram` is `kg` and not `k g`."""
        assert format_unit(r'\kilo\gram', sk) == r'\text{kg}'

    def test_a_range_repeats_the_unit(self, sk):
        """`range-units = repeat`, and the phrase is an en dash with spaces."""
        assert expand(r'\qtyrange{1}{2}{\metre}', sk) == '1\\ \\text{m – }2\\ \\text{m}'


class TestUnitSymbols:
    def test_the_locale_table_wins(self, sk):
        """`override.jtex` re-declares units per language; the page must follow the booklet."""
        assert symbol('metre', sk) == r'\text{m}'

    def test_a_custom_declaration_is_read_from_siunitx_tex(self, sk):
        """Not copied into a second table -- parsed from the file the booklet itself loads."""
        assert symbol('watthour', sk) == r'\text{Wh}'

    def test_a_declared_symbol_is_made_safe_for_maths(self, sk):
        """
        `siunitx.tex` writes Celsius as `\\text{°}C`, which leaves the `C` in maths and italic.
        """
        assert symbol('celsius', sk) == r'\text{°}\text{C}'
        assert expand(r'\qty{10}{\celsius}', sk) == r'10\ \text{°C}'

    def test_markup_already_inside_a_group_is_left_alone(self, sk):
        assert symbol('gforce', sk) == r'\textit{g}'


class TestEmptyArgument:
    """
    `\\num{}` is not a number, and it must not be a crash either.

    `value[:1] in '+-'` is true for the empty string -- every string contains the empty one --
    so the sign test used to index `value[0]` and raise `IndexError` out of a preprocess that
    names neither the file nor the line. A specimen volume writing `\\num{}` in prose about the
    macro took the whole HTML build down with it.
    """
    def test_empty_number_is_empty(self, en):
        assert expand(r'\num{}', en) == ''

    def test_empty_quantity_keeps_its_unit(self, en):
        assert expand(r'\qty{}{\metre}', en) == r'\ \text{m}'

    def test_a_sign_is_still_a_sign(self, en):
        """The quiet half: a real leading sign must survive the fix."""
        assert expand(r'\num{-1.5}', en) == '-1.5'
        assert expand(r'\num{+15}', en) == '+15'


class TestItLeavesEverythingElseAlone:
    """The quiet half, and the one that matters: this runs over every line of every document."""

    @pytest.mark.parametrize('text', [
        'Ordinary prose with no maths in it at all.',
        r'$E = \frac{1}{2} m v^2$',
        r'A \textbf{bold} word and a \qtyfoot that is not a command.',
        r'\section{Numbers}',
        '',
    ])
    def test_untouched(self, sk, text):
        assert expand(text, sk) == text

    def test_a_call_it_cannot_parse_is_left_standing(self, sk):
        """
        Better a visible `\\qty` than a silently mangled number -- an unbalanced argument means
        something else is wrong and should be seen.
        """
        assert expand(r'\qty{3}{', sk) == r'\qty{3}{'

    def test_surrounding_text_survives(self, sk):
        assert expand(r'before \qty{3}{\metre} after', sk) == r'before 3\ \text{m} after'

    def test_a_nested_argument_is_read_whole(self, sk):
        assert expand(r'\num{\frac{1}{2}}', sk) == r'\frac{1}{2}'

    def test_an_option_list_is_stepped_over(self, sk):
        assert expand(r'\qty[per-mode=symbol]{3}{\metre}', sk) == r'3\ \text{m}'

    def test_an_unknown_unit_stays_visible(self, sk):
        """`\\kg` is not a siunitx unit and is an authoring error; it must not vanish."""
        assert r'\kg' in expand(r'\qty{90}{\kg}', sk)


class TestComputedPowers:
    r"""
    `\tothe{n}` and `\raiseto{n}` are siunitx's argument-taking powers.

    They arrive from the quantity formatter rather than from an author: a unit whose exponent is
    not 2 or 3 has no `\squared`/`\cubed` to reach for, so the cube root of a volume in litres is
    `\litre\tothe{0.333}`. The chain parser used to collect macro *names* only, so the argument
    was dropped and `\tothe` reached the page as a red undefined macro beside a unit with no
    power on it at all.
    """

    def test_a_fractional_power_keeps_its_exponent(self, en):
        assert format_unit(r'\litre\tothe{0.333}', en) == r'\text{l}^{0.333}'

    def test_raiseto_is_the_same(self, en):
        assert format_unit(r'\metre\raiseto{1.5}', en) == r'\text{m}^{1.5}'

    def test_the_named_powers_still_work(self, en):
        assert format_unit(r'\metre\squared', en) == r'\text{m}^{2}'
        assert format_unit(r'\kilo\gram\per\metre\cubed', en) == r'\text{kg}/\text{m}^{3}'


class TestTheSettingsComeFromTheDocument:
    r"""
    Half of `core/latex/siunitx.tex` was parsed and half transcribed, thirty lines apart in the
    same module. The `\DeclareSIUnit` half had always been read "so a unit added there reaches
    the web without anybody remembering a second table"; the `\sisetup` half was seven constants
    typed out again, with nothing comparing them. Change `group-minimum-digits` for the booklet
    and the web began grouping at a different width in every fragment, silently.
    """

    def sisetup(self):
        return siunitx._setup()

    @pytest.mark.parametrize(('key', 'name'), [
        ('exponent-product', 'EXPONENT_PRODUCT'),
        ('number-unit-product', 'NUMBER_UNIT_PRODUCT'),
        ('group-separator', 'GROUP_SEPARATOR'),
    ])
    def test_a_separator_is_the_documents_own(self, key, name):
        assert getattr(siunitx, name) == self.sisetup()[key]

    def test_the_grouping_width_is_the_documents_own(self):
        assert siunitx.GROUP_MINIMUM_DIGITS == int(self.sisetup()['group-minimum-digits'])

    def test_per_mode_is_translated_rather_than_copied(self):
        r"""
        `per-mode` names a behaviour -- `symbol` means `m/s`, `reciprocal` would mean
        `m\,s^{-1}` -- so this one is a mapping and not a value. Only the mode the document sets
        is implemented, and this is what says so if that ever changes.
        """
        assert self.sisetup()['per-mode'] == 'symbol'
        assert siunitx.PER == '/'

    def test_the_two_divergences_are_deliberate_and_still_diverge(self):
        r"""
        The quiet case, and the reason this is not simply "read everything". MathJax has no
        `--` ligature and no `\allowbreak`, so these two are *supposed* to differ from what
        `\sisetup` says. A test asserting equality would be wrong; what is worth pinning is that
        each still differs in exactly the one documented way.
        """
        setup = self.sisetup()
        assert setup['range-phrase'] == r'\text{ -- }'
        assert siunitx.RANGE_PHRASE == '\\text{ – }', 'an en dash outright, not the ligature'

        assert r'\allowbreak' in setup['list-separator']
        assert r'\allowbreak' not in siunitx.LIST_SEPARATOR
        assert siunitx.LIST_SEPARATOR == setup['list-separator'].replace(r'\allowbreak', '')

    def test_every_key_the_module_reads_is_in_the_file(self):
        """A `\\sisetup` key renamed upstream would otherwise fall back to a default quietly."""
        setup = self.sisetup()
        for key in ('per-mode', 'exponent-product', 'number-unit-product',
                    'group-separator', 'group-minimum-digits', 'range-phrase', 'list-separator'):
            assert key in setup, f'{key} is no longer in the sisetup block'


class TestTheUnitTableNoticesAnEdit:
    def test_a_unit_added_to_the_file_is_seen_without_a_restart(self, tmp_path):
        """
        `declared_units` was `@functools.cache`d on a path, so the editor -- which serves for
        hours -- went on reporting a newly declared unit as `unit-unknown`, and went on letting
        it reach the page unexpanded, until somebody restarted the server.
        """
        declarations = tmp_path / 'siunitx.tex'
        declarations.write_text('\\DeclareSIUnit{\\widget}{wd}\n')
        assert siunitx.declared_units(str(declarations)) == {'widget': 'wd'}

        declarations.write_text('\\DeclareSIUnit{\\widget}{wd}\n\\DeclareSIUnit{\\sprocket}{sp}\n')
        assert set(siunitx.declared_units(str(declarations))) == {'widget', 'sprocket'}

    def test_a_file_that_has_not_changed_is_not_reread(self, tmp_path, monkeypatch):
        """The quiet half: the cache still is one, or every formula would re-read the file."""
        declarations = tmp_path / 'siunitx.tex'
        declarations.write_text('\\DeclareSIUnit{\\widget}{wd}\n')
        siunitx.declared_units(str(declarations))
        before = siunitx._declared_at.cache_info().hits
        siunitx.declared_units(str(declarations))
        assert siunitx._declared_at.cache_info().hits == before + 1
