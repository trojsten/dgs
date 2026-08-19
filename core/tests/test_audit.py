"""
Tests for the source-only audit checks.

Every check gets two tests: one that it fires on the thing it is for, and one that it stays quiet on
a case that looks like that thing and is not. The second half is the point. Each of those quiet
cases is a false positive that a hand-written version of the same sweep actually produced while
volumes 19 to 29 were being audited, and every one of them cost time to chase down.
"""
import pathlib
import re

import pytest
import yaml

from core.audit import audit
from core.audit.checks import magnitudes, si_calls, strip_maths_whitespace
from core.audit.sources import (SHARED_FILES, TRANSLATED_FILES,
                               read_scope)
from core.audit.status import translation_status


def make_problem(tmp_path, name='widget', meta='authors:\n  idea: []\n  problem: []\n'
                                                '  solution: []\ntags: [\'kinematics\']\n',
                 files=None, shared=None, assets=()):
    """A problem directory. `files` is {language: {filename: text}}, `shared` is {filename: text}."""
    root = tmp_path / 'phys' / '99' / 'problems' / name
    root.mkdir(parents=True)
    if meta is not None:
        (root / 'meta.yaml').write_text(meta)
    for filename, text in (shared or {}).items():
        (root / filename).write_text(text)
    for lang, contents in (files or {}).items():
        (root / lang).mkdir(exist_ok=True)
        for filename, text in contents.items():
            (root / lang / filename).write_text(text)
    for asset in assets:
        (root / asset).write_text('<svg/>')
    return root


def run(tmp_path, **kwargs):
    make_problem(tmp_path, **kwargs)
    return audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/' + kwargs.get('name', 'widget')])


def volume_meta(tmp_path, problems):
    """The volume's own meta.yaml -- the `problems:` list is the running order and the build list."""
    (tmp_path / 'phys' / '99').mkdir(parents=True, exist_ok=True)
    listed = ''.join(f'  - {p}\n' for p in problems)
    (tmp_path / 'phys' / '99' / 'meta.yaml').write_text(f'problems:\n{listed}')


def ids(report):
    return {f.check for f in report.findings}


class TestSiunitxParsing:
    """Arity, because reading a range as if it were a `\\qty` invents findings out of nothing."""

    @pytest.mark.parametrize('text, values, unit', [
        (r'\qty{200}{\kilo\gram}', ['200'], r'\kilo\gram'),
        (r'\qty[per-mode=symbol]{200}{\kilo\gram}', ['200'], r'\kilo\gram'),
        (r'\qtyrange{0}{30}{\celsius}', ['0', '30'], r'\celsius'),
        (r'\qtylist{20;30;60}{\ohm}', ['20;30;60'], r'\ohm'),
        (r'\num{1.25}', ['1.25'], None),
        (r'\ang{40}', ['40'], None),
    ])
    def test_arity(self, text, values, unit):
        call, = si_calls(text)
        assert call.values == values
        assert call.unit == unit

    def test_option_group_does_not_hide_the_call(self):
        # the first version of this regex had no option group, so every `\qty[...]` was invisible
        # and the cross-language comparison reported disagreements that did not exist
        assert magnitudes(r'\qty[per-mode=symbol]{200}{\kilo\gram}') == {'200': 1}

    def test_whitespace_between_arguments(self):
        # TeX skips it, so we must: two Russian statements looked as though they lacked a number
        assert si_calls(r'\qty{10} {\centi\metre}').__next__().unit == r'\centi\metre'
        assert si_calls('\\qty{0.3}\n{\\metre}').__next__().unit == r'\metre'

    def test_range_matches_two_separate_quantities(self):
        # `\qtyrange{0}{30}{\celsius}` and `\qty{0}{\celsius} až \qty{30}{\celsius}` say the same
        # thing; 21/flat-earth writes it each way and they must not read as a disagreement
        assert magnitudes(r'\qtyrange{0}{30}{\celsius}') == \
               magnitudes(r'\qty{0}{\celsius} a \qty{30}{\celsius}')


class TestMathsWhitespace:
    def test_maths_whitespace_is_not_significant(self):
        assert strip_maths_whitespace(r'\frac{1}{2^n k}') == strip_maths_whitespace(r'\frac{1}{2^nk}')

    def test_text_whitespace_is_significant(self):
        # inside \text{} it is real text, and a difference there is a translated word
        assert strip_maths_whitespace(r'\text{a b}') != strip_maths_whitespace(r'\text{ab}')


class TestMetadata:
    def test_meta_missing(self, tmp_path):
        assert 'meta-missing' in ids(run(tmp_path, meta=None))

    def test_meta_empty(self, tmp_path):
        assert 'meta-empty' in ids(run(tmp_path, meta=''))

    def test_meta_unparseable(self, tmp_path):
        assert 'meta-unparseable' in ids(run(tmp_path, meta='authors: [\n'))

    def test_meta_invalid(self, tmp_path):
        assert 'meta-invalid' in ids(run(tmp_path, meta='tags: []\n'))

    def test_valid_meta_is_quiet(self, tmp_path):
        assert not {'meta-missing', 'meta-empty', 'meta-invalid'} & ids(run(tmp_path))

    def test_authors_empty(self, tmp_path):
        assert 'authors-empty' in ids(run(tmp_path))

    def test_author_placeholder(self, tmp_path):
        meta = ("authors:\n  idea: ['unknown']\n  problem: []\n  solution: []\n"
                "tags: ['kinematics']\n")
        assert 'author-placeholder' in ids(run(tmp_path, meta=meta))

    def test_question_mark_is_the_unknown_marker(self, tmp_path):
        # `?` is what this repo writes for "not recorded" -- chem/04 uses it in all 36 problems --
        # so it counts as unrecorded rather than as a name that would be typeset
        meta = "authors:\n  idea: ['?']\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
        report = run(tmp_path, meta=meta)
        assert 'author-placeholder' not in ids(report)
        assert 'authors-empty' in ids(report)
        assert report.stats.authors == {}

    def test_real_author_is_quiet(self, tmp_path):
        meta = "authors:\n  idea: ['Kvík']\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
        found = ids(run(tmp_path, meta=meta))
        assert 'author-placeholder' not in found and 'authors-empty' not in found

    def test_tags_empty(self, tmp_path):
        meta = 'authors:\n  idea: []\n  problem: []\n  solution: []\ntags: []\n'
        assert 'tags-empty' in ids(run(tmp_path, meta=meta))

    def test_tag_unknown(self, tmp_path):
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\n"
                "tags: ['not-a-real-tag']\n")
        assert 'tag-unknown' in ids(run(tmp_path, meta=meta))


class TestMaths:
    def test_left_right_unbalanced(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n    \\left(2M + m)g\n$$\n'}}
        assert 'left-right-unbalanced' in ids(run(tmp_path, files=files))

    def test_rightarrow_is_not_a_right(self, tmp_path):
        # `\rightarrow` contains `\right`; the naive version reported every cycle problem
        files = {'sk': {'problem.md': '$$\n    1 \\rightarrow 2 \\rightarrow 3\n$$\n'}}
        assert 'left-right-unbalanced' not in ids(run(tmp_path, files=files))

    def test_right_before_a_newline_is_fine(self, tmp_path):
        # `\right` is a control word, so TeX skips the newline to find its delimiter --
        # 24/cominterna writes it this way in two languages and it compiles
        files = {'sk': {'solution.md': '$$\n    x \\left[\n        y\\right\n    ]\n$$\n'}}
        assert 'left-right-unbalanced' not in ids(run(tmp_path, files=files))

    def test_dollar_unpaired(self, tmp_path):
        files = {'en': {'problem.md': 'was $\\qty{255}{\\second}$ and \\qty{285}{\\second}$ of\n'}}
        assert 'dollar-unpaired' in ids(run(tmp_path, files=files))

    def test_escaped_dollar_is_not_a_delimiter(self, tmp_path):
        files = {'en': {'problem.md': 'it costs \\$5 and $x$ is fine\n'}}
        assert 'dollar-unpaired' not in ids(run(tmp_path, files=files))

    def test_block_indent(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n   z = 1\n$$\n'}}
        assert 'block-indent' in ids(run(tmp_path, files=files))

    def test_four_space_indent_is_quiet(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n    z = 1\n$$\n'}}
        assert 'block-indent' not in ids(run(tmp_path, files=files))

    def test_deeper_indent_is_kept(self, tmp_path):
        # only the *minimum* matters; a continuation line lines up under an `&=`
        files = {'sk': {'solution.md': '$${\n    a &= b \\\\\n        &= c\n}$$\n'}}
        assert 'block-indent' not in ids(run(tmp_path, files=files))

    def test_aligned_longhand(self, tmp_path):
        files = {'sk': {'solution.md':
                        '$$\n\\begin{aligned}\n    a &= b\n\\end{aligned}\n$$\n'}}
        assert 'aligned-longhand' in ids(run(tmp_path, files=files))

    def test_short_form_is_quiet(self, tmp_path):
        files = {'sk': {'solution.md': '$${\n    a &= b\n}$$\n'}}
        assert 'aligned-longhand' not in ids(run(tmp_path, files=files))

    def test_delimiter_indented(self, tmp_path):
        files = {'hu': {'solution.md': ' $$\n    a = b\n$$\n'}}
        assert 'delimiter-indented' in ids(run(tmp_path, files=files))

    def test_indented_delimiter_suppresses_block_checks(self, tmp_path):
        """
        The reason this check exists. With a delimiter at column one, `^$$` pairs one block's
        closing marker with the next block's opener and reads the prose between them as maths, so
        every block-level finding in that file is nonsense. Report the cause, not the symptoms.
        """
        files = {'hu': {'solution.md': ' $$\n    a = b\n$$\n\nprose\n\n$$\n    c = d\n$$\n'}}
        found = ids(run(tmp_path, files=files))
        assert 'delimiter-indented' in found
        assert 'block-indent' not in found

    def test_double_backslash_macro(self, tmp_path):
        files = {'hu': {'solution.md': '$${\n    a &= 0 \\\\QQText{és} b\n}$$\n'}}
        assert 'double-backslash-macro' in ids(run(tmp_path, files=files))

    def test_row_break_is_quiet(self, tmp_path):
        files = {'sk': {'solution.md': '$${\n    a &= b \\\\\n    c &= d\n}$$\n'}}
        assert 'double-backslash-macro' not in ids(run(tmp_path, files=files))


class TestLabels:
    def test_label_schema(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n    a = b\n$$ {#eq:widget-first}\n'}}
        assert 'label-schema' in ids(run(tmp_path, files=files))

    def test_conforming_label_is_quiet(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n    a = b\n$$ {#eq:widget:first}\n'}}
        assert 'label-schema' not in ids(run(tmp_path, files=files))

    def test_reference_dangling(self, tmp_path):
        files = {'sk': {'solution.md': 'see [-@eq:widget:nowhere]\n'}}
        assert 'reference-dangling' in ids(run(tmp_path, files=files))

    def test_reference_to_a_hoisted_equation_is_quiet(self, tmp_path):
        # a hoisted equation defines its label in meta.yaml, not in any source; a checker that
        # reads only the sources calls every one of them a broken reference
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "eq:\n  first: 'a = b'\n")
        files = {'sk': {'solution.md': 'see [-@eq:widget:first]\n'}}
        assert 'reference-dangling' not in ids(run(tmp_path, meta=meta, files=files))

    def test_section_reference_is_quiet(self, tmp_path):
        # the templates emit \label{sec:<problem>:problem} for every problem
        files = {'sk': {'solution.md': 'as in [-@sec:widget:problem]\n'}}
        assert 'reference-dangling' not in ids(run(tmp_path, files=files))


class TestSiunitxChecks:
    def test_literal_unit(self, tmp_path):
        files = {'en': {'problem.md': 'it is $\\qty{100}{km}$ away\n'}}
        assert 'literal-unit' in ids(run(tmp_path, files=files))

    def test_licensed_literal_unit_is_quiet(self, tmp_path):
        files = {'en': {'problem.md':
                        'a rod $\\qty[forbid-literal-units=false]{1}{grrrr}$ long\n'}}
        assert 'literal-unit' not in ids(run(tmp_path, files=files))

    def test_range_second_number_is_not_a_unit(self, tmp_path):
        # reading `\qtyrange{0}{30}{\celsius}` as `\qty` makes `30` look like a literal unit
        files = {'en': {'problem.md': 'between $\\qtyrange{0}{30}{\\celsius}$\n'}}
        assert 'literal-unit' not in ids(run(tmp_path, files=files))

    def test_symbolic_number(self, tmp_path):
        files = {'en': {'problem.md': 'area $S = \\qty{\\pi}{\\milli\\metre\\squared}$\n'}}
        assert 'symbolic-number' in ids(run(tmp_path, files=files))

    def test_uncertainty_is_quiet(self, tmp_path):
        files = {'en': {'problem.md': 'half-life $\\qty{5730 \\pm 40}{\\year}$\n'}}
        assert 'symbolic-number' not in ids(run(tmp_path, files=files))

    def test_bare_exponent_is_quiet(self, tmp_path):
        # `\qty{e13}{...}` means 10^13; valid siunitx, and the spelling this repo prefers
        files = {'en': {'problem.md': 'about $\\qty{e13}{\\metre}$\n'}}
        assert 'symbolic-number' not in ids(run(tmp_path, files=files))

    def test_list_is_quiet(self, tmp_path):
        files = {'en': {'problem.md': 'resistors $\\qtylist{20;30;60}{\\ohm}$\n'}}
        assert 'symbolic-number' not in ids(run(tmp_path, files=files))

    def test_degrees_minutes_seconds_is_quiet(self, tmp_path):
        files = {'en': {'problem.md': 'latitude $\\ang{30;15;0}$\n'}}
        assert 'symbolic-number' not in ids(run(tmp_path, files=files))


class TestTranslations:
    def test_magnitude_disagreement(self, tmp_path):
        files = {'sk': {'problem.md': 'a $\\qty{30}{\\metre}$ pole\n'},
                 'en': {'problem.md': 'a $\\qty{40}{\\metre}$ pole\n'}}
        assert 'magnitude-disagreement' in ids(run(tmp_path, files=files))

    def test_agreeing_translations_are_quiet(self, tmp_path):
        files = {'sk': {'problem.md': 'a $\\qty{30}{\\metre}$ pole\n'},
                 'en': {'problem.md': 'a $\\qty{30}{\\meter}$ pole\n'}}
        assert 'magnitude-disagreement' not in ids(run(tmp_path, files=files))

    def test_a_jinja_tag_is_the_same_everywhere(self, tmp_path):
        # a tag reads from meta.yaml, so it cannot differ; only literals can
        files = {'sk': {'problem.md': 'a $(§ h §)$ pole\n'},
                 'en': {'problem.md': 'a $(§ h §)$ pole\n'}}
        assert 'magnitude-disagreement' not in ids(run(tmp_path, files=files))

    def test_hardcoded_value(self, tmp_path):
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "values:\n  h:\n    magnitude: 30\n    unit: 'metre'\n")
        files = {'sk': {'problem.md': 'a $(§ h §)$ pole\n'},
                 'en': {'problem.md': 'a $\\qty{30}{\\metre}$ pole\n'}}
        assert 'hardcoded-value' in ids(run(tmp_path, meta=meta, files=files))

    def test_presence(self, tmp_path):
        files = {'sk': {'problem.md': 'x\n', 'solution.md': 'y\n'}, 'en': {'problem.md': 'x\n'}}
        assert 'presence' in ids(run(tmp_path, files=files))

    def test_matching_languages_are_quiet(self, tmp_path):
        files = {'sk': {'problem.md': 'x\n'}, 'en': {'problem.md': 'x\n'}}
        assert 'presence' not in ids(run(tmp_path, files=files))


class TestFiles:
    def test_insert_picture(self, tmp_path):
        files = {'sk': {'problem.md': '\\insertPicture{belt.pdf}{40mm}\n'}}
        assert 'insert-picture' in ids(run(tmp_path, files=files))

    def test_markdown_figure_is_quiet(self, tmp_path):
        files = {'sk': {'problem.md': '![](belt.svg){height=40mm}\n'}}
        report = run(tmp_path, files=files, assets=('belt.svg',))
        assert not {'insert-picture', 'figure-missing', 'figure-unsized'} & ids(report)

    def test_figure_missing(self, tmp_path):
        files = {'sk': {'problem.md': '![](nope.svg){height=40mm}\n'}}
        assert 'figure-missing' in ids(run(tmp_path, files=files))

    def test_figure_unsized(self, tmp_path):
        files = {'sk': {'problem.md': '![](belt.svg)\n'}}
        assert 'figure-unsized' in ids(run(tmp_path, files=files, assets=('belt.svg',)))

    def test_asset_unused(self, tmp_path):
        assert 'asset-unused' in ids(run(tmp_path, assets=('orphan.svg',)))

    def test_encoding(self, tmp_path):
        files = {'sk': {'problem.md': 'trailing   \nand\ttab\n'}}
        assert 'encoding' in ids(run(tmp_path, files=files))

    def test_clean_file_is_quiet(self, tmp_path):
        files = {'sk': {'problem.md': 'nothing wrong here\n'}}
        assert 'encoding' not in ids(run(tmp_path, files=files))


class TestHoisting:
    def test_hoistable_equation(self, tmp_path):
        block = '$$\n    a = b\n$$ {#eq:widget:first}\n'
        files = {'sk': {'solution.md': block}, 'en': {'solution.md': block}}
        report = run(tmp_path, files=files)
        assert 'hoistable-equation' in ids(report)
        assert 'identical' in [f.message for f in report.findings
                               if f.check == 'hoistable-equation'][0]

    def test_whitespace_does_not_block_hoisting(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n    a = b\n$$ {#eq:widget:first}\n'},
                 'en': {'solution.md': '$$\n    a =\n    b\n$$ {#eq:widget:first}\n'}}
        message, = [f.message for f in run(tmp_path, files=files).findings
                    if f.check == 'hoistable-equation']
        assert 'identical' in message

    def test_trailing_punctuation_does_not_block_hoisting(self, tmp_path):
        # `MathObject` carries it in the format spec: |disp('.') in one place, |disp in the other
        files = {'sk': {'solution.md': '$$\n    a = b.\n$$ {#eq:widget:first}\n'},
                 'en': {'solution.md': '$$\n    a = b\n$$ {#eq:widget:first}\n'}}
        message, = [f.message for f in run(tmp_path, files=files).findings
                    if f.check == 'hoistable-equation']
        assert 'identical' in message

    def test_a_translated_subscript_does_block_hoisting(self, tmp_path):
        files = {'sk': {'solution.md':
                        '$$\n    Q_{\\text{prijaté}} = 0\n$$ {#eq:widget:first}\n'},
                 'en': {'solution.md':
                        '$$\n    Q_{\\text{absorbed}} = 0\n$$ {#eq:widget:first}\n'}}
        message, = [f.message for f in run(tmp_path, files=files).findings
                    if f.check == 'hoistable-equation']
        assert 'variants' in message

    def test_one_copy_is_not_hoistable(self, tmp_path):
        files = {'sk': {'solution.md': '$$\n    a = b\n$$ {#eq:widget:first}\n'}}
        assert 'hoistable-equation' not in ids(run(tmp_path, files=files))


class TestOptOut:
    def test_a_problem_can_ignore_a_check(self, tmp_path):
        """
        Some findings are the point of the problem: `23/grammar-nazi` is deliberately misspelled,
        and `23/bats`, `27/escalator` and `28/john-doe` have invented units.
        """
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "audit:\n  ignore: ['literal-unit']\n")
        files = {'en': {'problem.md': 'a rod $\\qty{1}{grrrr}$ long\n'}}
        assert 'literal-unit' not in ids(run(tmp_path, meta=meta, files=files))

    def test_the_opt_out_is_per_check(self, tmp_path):
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "audit:\n  ignore: ['encoding']\n")
        files = {'en': {'problem.md': 'a rod $\\qty{1}{grrrr}$ long\n'}}
        assert 'literal-unit' in ids(run(tmp_path, meta=meta, files=files))


class TestLiteralUnitWrappers:
    def test_text_wrapped_unit_is_still_literal(self, tmp_path):
        # siunitx refuses `\text{...}` in a unit argument exactly as it refuses bare text;
        # chem/01/zaklínač writes `\qty{522}{\text{ľudí}}` and its solutions target would not build
        files = {'sk': {'solution.md': 'poisons $\\qty{522}{\\text{ľudí}}$\n'}}
        assert 'literal-unit' in ids(run(tmp_path, files=files))

    def test_licensed_text_wrapped_unit_is_quiet(self, tmp_path):
        files = {'sk': {'solution.md':
                        '$\\qty[forbid-literal-units=false]{1}{\\text{konská hmotnosť}}$\n'}}
        assert 'literal-unit' not in ids(run(tmp_path, files=files))

    def test_real_units_are_quiet(self, tmp_path):
        files = {'sk': {'solution.md': '$\\qty{645.746}{\\gram\\per\\mole}$\n'}}
        assert 'literal-unit' not in ids(run(tmp_path, files=files))

    def test_text_mixed_with_a_real_macro_is_literal(self, tmp_path):
        # `rok\tothe{-1}` has a backslash in it and is still literal text; a genuine unit argument
        # is macros all the way down. chem/01/rádiouhlík wrote this and would not compile.
        files = {'sk': {'solution.md':
                        '$\\qty[per-mode=reciprocal]{1.21e-4}{rok\\tothe{-1}}$\n'}}
        assert 'literal-unit' in ids(run(tmp_path, files=files))

    def test_a_macro_unit_with_an_exponent_is_quiet(self, tmp_path):
        files = {'sk': {'solution.md': '$\\qty{1}{\\metre\\tothe{-1}}$\n'}}
        assert 'literal-unit' not in ids(run(tmp_path, files=files))


def statuses_of(tmp_path, **kwargs):
    """The four status verdicts for a single problem."""
    report = run(tmp_path, **kwargs)
    name = kwargs.get('name', 'widget')
    return report.statuses[f'phys/99/problems/{name}']


class TestTranslationStatus:
    def test_all_languages_written(self, tmp_path):
        files = {l: {'problem.md': 'x\n', 'solution.md': 'y\n'} for l in ('sk', 'en')}
        assert statuses_of(tmp_path, files=files)['translations'].state == 'ok'

    def test_a_missing_language(self, tmp_path):
        files = {'sk': {'problem.md': 'x\n', 'solution.md': 'y\n'},
                 'en': {'solution.md': 'y\n'}}
        status = statuses_of(tmp_path, files=files)['translations']
        assert status.state == 'missing'
        assert status.detail['languages']['en']['files']['problem.md']['state'] == 'missing'

    def test_an_empty_file(self, tmp_path):
        files = {'sk': {'problem.md': 'x\n', 'solution.md': 'y\n'},
                 'en': {'problem.md': 'x\n', 'solution.md': '   \n'}}
        status = statuses_of(tmp_path, files=files)['translations']
        assert status.state == 'partial'
        assert status.detail['languages']['en']['files']['solution.md']['state'] == 'empty'

    def test_a_mirrored_translation(self, tmp_path):
        """
        A translation nobody has written yet points at its master rather than keeping a stale copy.
        That is deliberate, and the status says which language it is waiting on.
        """
        root = make_problem(tmp_path, files={'sk': {'problem.md': 'x\n', 'solution.md': 'y\n'},
                                             'en': {'problem.md': 'x\n'}})
        (root / 'en' / 'solution.md').symlink_to('../sk/solution.md')
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        status = report.statuses['phys/99/problems/widget']['translations']
        entry = status.detail['languages']['en']['files']['solution.md']
        assert entry['state'] == 'symlink'
        assert 'mirrors sk' in entry['note']


class TestEquationStatus:
    def test_nothing_to_deduplicate(self, tmp_path):
        # One solution, so nothing is written out twice, which is the end state rather than a
        # not-applicable: volumes 19 and 23 have Slovak solutions only and are already there.
        files = {'sk': {'solution.md': '$$\n    a = b\n$$ {#eq:widget:first}\n'}}
        assert statuses_of(tmp_path, files=files)['equations'].state == 'ok'

    def test_no_equations_at_all(self, tmp_path):
        files = {'sk': {'solution.md': 'the answer is four\n'}}
        assert statuses_of(tmp_path, files=files)['equations'].state == 'none'

    def test_duplicated_and_not_hoisted(self, tmp_path):
        block = '$$\n    a = b\n$$ {#eq:widget:first}\n'
        files = {'sk': {'solution.md': block}, 'en': {'solution.md': block}}
        status = statuses_of(tmp_path, files=files)['equations']
        assert status.state == 'missing'
        assert status.detail['duplicated'] == ['first']

    def test_hoisted(self, tmp_path):
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "eq:\n  first: 'a = b'\n")
        files = {l: {'solution.md': '(§ eq.first|disp §)\n'} for l in ('sk', 'en')}
        assert statuses_of(tmp_path, meta=meta, files=files)['equations'].state == 'ok'

    def test_divergent_copies_cannot_be_hoisted(self, tmp_path):
        files = {'sk': {'solution.md':
                        '$$\n    Q_{\\text{prijaté}} = 0\n$$ {#eq:widget:first}\n'},
                 'en': {'solution.md':
                        '$$\n    Q_{\\text{absorbed}} = 0\n$$ {#eq:widget:first}\n'}}
        status = statuses_of(tmp_path, files=files)['equations']
        assert status.state == 'partial'
        assert status.detail['divergent'] == ['first']


class TestPictureStatus:
    def test_no_pictures(self, tmp_path):
        assert statuses_of(tmp_path)['pictures'].state == 'none'

    def test_properly_included(self, tmp_path):
        files = {'sk': {'problem.md': '![](belt.svg){height=40mm}\n'}}
        assert statuses_of(tmp_path, files=files,
                           assets=('belt.svg',))['pictures'].state == 'ok'

    def test_never_included(self, tmp_path):
        status = statuses_of(tmp_path, assets=('orphan.svg',))['pictures']
        assert status.state == 'partial'
        assert status.detail['unused'] == ['orphan.svg']

    def test_naming_the_built_file(self, tmp_path):
        """
        `x.pdf` where the repository holds `x.svg` still resolves, because make converts one into
        the other -- so it is a naming slip rather than a hole, and must not read as broken.
        """
        files = {'sk': {'problem.md': '![](belt.pdf){height=40mm}\n'}}
        status = statuses_of(tmp_path, files=files, assets=('belt.svg',))['pictures']
        assert status.state == 'partial'
        assert status.detail['misnamed'] and not status.detail['broken']

    def test_a_file_that_exists_nowhere_is_broken(self, tmp_path):
        files = {'sk': {'problem.md': '![](nope.svg){height=40mm}\n'}}
        status = statuses_of(tmp_path, files=files, assets=('belt.svg',))['pictures']
        assert status.state == 'broken'

    def test_a_malformed_target_is_broken(self, tmp_path):
        files = {'sk': {'solution.md': '![](belt.svg}{height=40mm}\n'}}
        report = run(tmp_path, files=files, assets=('belt.svg',))
        assert 'figure-malformed' in ids(report)


class TestValueStatus:
    def test_no_numbers(self, tmp_path):
        files = {l: {'problem.md': 'a rod of length $L$\n'} for l in ('sk', 'en')}
        assert statuses_of(tmp_path, files=files)['values'].state == 'none'

    def test_shared_number_not_extracted(self, tmp_path):
        files = {l: {'problem.md': 'a $\\qty{30}{\\metre}$ pole\n'} for l in ('sk', 'en')}
        status = statuses_of(tmp_path, files=files)['values']
        assert status.state == 'missing'
        assert status.detail['literal'] == ['30']

    def test_extracted(self, tmp_path):
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "values:\n  h:\n    magnitude: 30\n    unit: 'metre'\n")
        files = {l: {'problem.md': 'a $(§ h §)$ pole\n'} for l in ('sk', 'en')}
        assert statuses_of(tmp_path, meta=meta, files=files)['values'].state == 'ok'

    def test_partly_extracted(self, tmp_path):
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
                "values:\n  h:\n    magnitude: 30\n    unit: 'metre'\n")
        files = {l: {'problem.md': 'a $(§ h §)$ pole in $\\qty{5}{\\second}$\n'}
                 for l in ('sk', 'en')}
        assert statuses_of(tmp_path, meta=meta, files=files)['values'].state == 'partial'

    def test_a_number_in_only_one_language_is_not_evidence(self, tmp_path):
        # it appears in one translation and not the others, so it is a translation slip or something
        # incidental -- either way not a parameter of the problem
        files = {'sk': {'problem.md': 'a pole\n'},
                 'en': {'problem.md': 'a $\\qty{30}{\\metre}$ pole\n'}}
        assert statuses_of(tmp_path, files=files)['values'].state == 'none'


class TestVolumeListing:
    """
    The volume meta's `problems:` list is what `ContextVolume` iterates, so it decides both the
    order and what gets built at all. Volume 19 listed `onion` for years after the directory became
    `onion-capacity`: the booklet built, exited 0, and printed `Missing file ...!` on page 42.
    """

    def test_unlisted_problem_fires(self, tmp_path):
        make_problem(tmp_path, name='widget')
        volume_meta(tmp_path, ['something-else'])
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert 'unit-unlisted' in ids(report)

    def test_listed_problem_is_quiet(self, tmp_path):
        make_problem(tmp_path, name='widget')
        volume_meta(tmp_path, ['widget'])
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert 'unit-unlisted' not in ids(report)

    def test_no_volume_meta_is_quiet(self, tmp_path):
        """A scope with no list to check against is not a scope where everything is unlisted."""
        assert 'unit-unlisted' not in ids(run(tmp_path))

    def test_listed_with_no_directory_fires(self, tmp_path):
        make_problem(tmp_path, name='widget')
        volume_meta(tmp_path, ['widget', 'onion'])
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert 'listed-missing' in ids(report)
        assert any('onion' in f.message for f in report.findings if f.check == 'listed-missing')

    def test_every_listed_problem_present_is_quiet(self, tmp_path):
        make_problem(tmp_path, name='widget')
        volume_meta(tmp_path, ['widget'])
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert 'listed-missing' not in ids(report)

    def test_order_follows_the_meta_not_the_alphabet(self, tmp_path):
        for name in ('alpha', 'beta', 'gamma'):
            make_problem(tmp_path, name=name)
        volume_meta(tmp_path, ['gamma', 'alpha', 'beta'])
        sources = read_scope(tmp_path, 'naboj', 'phys/99',
                             [f'phys/99/problems/{n}' for n in ('alpha', 'beta', 'gamma')])
        assert [u.name for u in sources.unit_list] == ['gamma', 'alpha', 'beta']
        assert [u.order for u in sources.unit_list] == [0, 1, 2]

    def test_unlisted_units_sort_last_and_keep_their_place(self, tmp_path):
        """An unlisted problem still has to appear, or the audit hides the thing worth seeing."""
        for name in ('alpha', 'beta', 'stray'):
            make_problem(tmp_path, name=name)
        volume_meta(tmp_path, ['beta', 'alpha'])
        sources = read_scope(tmp_path, 'naboj', 'phys/99',
                             [f'phys/99/problems/{n}' for n in ('alpha', 'beta', 'stray')])
        assert [u.name for u in sources.unit_list] == ['beta', 'alpha', 'stray']
        assert sources.unit_list[-1].order is None

    def test_fingerprint_ignores_the_order(self, tmp_path):
        """Reordering the meta must not call every cached build stale."""
        for name in ('alpha', 'beta'):
            make_problem(tmp_path, name=name)
        paths = ['phys/99/problems/alpha', 'phys/99/problems/beta']
        volume_meta(tmp_path, ['alpha', 'beta'])
        first = read_scope(tmp_path, 'naboj', 'phys/99', paths).fingerprint()
        volume_meta(tmp_path, ['beta', 'alpha'])
        assert read_scope(tmp_path, 'naboj', 'phys/99', paths).fingerprint() == first


class TestTranslationDetail:
    """
    The per-language columns read this, so it has to say what happened to every file -- not only
    the two that decide the verdict.
    """

    def _status(self, tmp_path, **kwargs):
        make_problem(tmp_path, **kwargs)
        sources = read_scope(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        return translation_status(sources.unit_list[0], ['sk', 'en'])

    def test_required_files_are_reported_per_language(self, tmp_path):
        s = self._status(tmp_path, files={'sk': {'problem.md': 'text', 'solution.md': 'text'},
                                          'en': {'problem.md': 'text'}})
        assert s.detail['languages']['sk']['files']['solution.md']['state'] == 'ok'
        assert s.detail['languages']['en']['files']['solution.md']['state'] == 'missing'

    def test_empty_is_not_missing(self, tmp_path):
        s = self._status(tmp_path, files={'sk': {'problem.md': 'text', 'solution.md': '  \n'},
                                          'en': {'problem.md': 'text', 'solution.md': 'text'}})
        assert s.detail['languages']['sk']['files']['solution.md']['state'] == 'empty'

    def test_an_optional_extra_is_reported_where_it_is_absent(self, tmp_path):
        """Once one language carries an extra, another not carrying it is a gap worth showing."""
        s = self._status(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'b', 'answer-extra.md': 'c'},
            'en': {'problem.md': 'a', 'solution.md': 'b'},
        })
        assert s.detail['languages']['en']['files']['answer-extra.md']['state'] == 'missing'
        assert s.detail['languages']['sk']['files']['answer-extra.md']['required'] is False
        assert s.detail['languages']['sk']['files']['problem.md']['required'] is True

    def test_an_absent_optional_extra_does_not_spoil_the_verdict(self, tmp_path):
        """`trans` answers "is this translated"; an answer sheet extra does not change the answer."""
        s = self._status(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'b', 'answer-extra.md': 'c'},
            'en': {'problem.md': 'a', 'solution.md': 'b'},
        })
        assert s.detail['languages']['en']['state'] == 'ok'
        assert s.state == 'ok'

    def test_no_extras_means_only_the_required_two(self, tmp_path):
        s = self._status(tmp_path, files={'sk': {'problem.md': 'a', 'solution.md': 'b'},
                                          'en': {'problem.md': 'a', 'solution.md': 'b'}})
        assert s.detail['order'] == ['problem.md', 'solution.md']

    def test_a_mirror_names_the_language_it_mirrors(self, tmp_path):
        """The cell shows `\u2192en`, so the target has to be a field and not only prose."""
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'b'},
                            'en': {'problem.md': 'a'}})
        link = tmp_path / 'phys' / '99' / 'problems' / 'widget' / 'en' / 'solution.md'
        link.symlink_to('../sk/solution.md')
        sources = read_scope(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        entry = (translation_status(sources.unit_list[0], ['sk', 'en'])
                 .detail['languages']['en']['files']['solution.md'])
        assert entry['state'] == 'symlink'
        assert entry['language'] == 'sk'

    def test_a_link_that_is_not_a_language_names_none(self, tmp_path):
        """`link_language` returning None must not put a path fragment in a two-character cell."""
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'b'},
                            'en': {'problem.md': 'a'}})
        elsewhere = tmp_path / 'phys' / '99' / 'shared-solution.md'
        elsewhere.write_text('b')
        link = tmp_path / 'phys' / '99' / 'problems' / 'widget' / 'en' / 'solution.md'
        link.symlink_to('../../../shared-solution.md')
        sources = read_scope(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        entry = (translation_status(sources.unit_list[0], ['sk', 'en'])
                 .detail['languages']['en']['files']['solution.md'])
        assert entry['state'] == 'symlink'
        assert entry['language'] is None
        assert 'shared-solution.md' in entry['note']

    def test_a_missing_language_directory_has_no_file_detail(self, tmp_path):
        """One dash for the language, not one mark per file it does not have."""
        s = self._status(tmp_path, files={'sk': {'problem.md': 'a', 'solution.md': 'b'}})
        assert s.detail['languages']['en'] == {'state': 'missing', 'note': 'no directory'}


class TestFileFamiliesMatchTheBuild:
    """
    `modules/naboj/editor.yaml` mirrors module.mk's two rule families, and the audit page reads the
    mirror. If module.mk gains a file and the descriptor does not, the page silently stops having a
    column for it -- so the mirror is pinned here rather than trusted.
    """

    def families_from_make(self):
        text = pathlib.Path('modules/naboj/module.mk').read_text()
        out = {}
        for macro, key in (('NABOJ_TRANSLATABLE', 'translated'),
                           ('NABOJ_NONTRANSLATABLE', 'shared')):
            m = re.search(r'\$\(foreach filename,([^,]+),\$\(eval \$\(call ' + macro, text)
            assert m, f"no foreach driving {macro} in module.mk"
            out[key] = m.group(1).split()
        return out

    def families_from_descriptor(self):
        spec = yaml.safe_load(pathlib.Path('modules/naboj/editor.yaml').read_text())
        kind = spec['units'][0]
        translated = list(kind['translated'])
        shared = [t for t in kind['targets'] if t not in translated]
        return {'translated': translated, 'shared': shared}

    def test_the_descriptor_lists_what_module_mk_builds(self):
        make = self.families_from_make()
        desc = self.families_from_descriptor()
        assert sorted(desc['translated']) == sorted(make['translated'])
        assert sorted(desc['shared']) == sorted(make['shared'])

    def test_the_audit_defaults_match_the_descriptor(self):
        """`core.audit` falls back to its own copy when no caller says; it must be the same copy."""
        desc = self.families_from_descriptor()
        assert sorted(TRANSLATED_FILES) == sorted(f'{n}.md' for n in desc['translated'])
        assert sorted(SHARED_FILES) == sorted(f'{n}.md' for n in desc['shared'])

    def test_a_file_the_rules_define_is_a_column_even_where_nothing_has_it(self, tmp_path):
        """`present_translated` narrows to the volume; the rules decide the order and the vocabulary."""
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'answer-extra.md': 'c'}})
        s = read_scope(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert s.present_translated() == ('problem.md', 'answer-extra.md')

    def test_an_unexpected_file_is_not_hidden(self, tmp_path):
        """A file no rule defines still has to show up, or the table lies by omission."""
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'b', 'notes.md': 'c'}})
        s = read_scope(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        st = translation_status(s.unit_list[0], ['sk'], s.translated_files)
        assert 'notes.md' in st.detail['order']

    def test_shared_files_are_reported_from_the_rules(self, tmp_path):
        make_problem(tmp_path, name='widget',
                     shared={'answer.md': '42', 'answer-interval.md': '40-44'},
                     files={'sk': {'problem.md': 'a', 'solution.md': 'b'}})
        s = read_scope(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert s.present_shared() == ('answer.md', 'answer-interval.md')


class TestHoistableKeys:
    """A suggestion that cannot be carried out is worse than no suggestion."""

    def _twice(self, tmp_path, label):
        block = ('$$\n    x = 1\n$$ {#eq:widget:' + label + '}\n')
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'text\n' + block},
                            'en': {'problem.md': 'a', 'solution.md': 'text\n' + block}})
        return ids(audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget']))

    def test_a_plain_label_is_reported(self, tmp_path):
        assert 'hoistable-equation' in self._twice(tmp_path, 'tau')

    def test_a_hyphenated_label_is_not(self, tmp_path):
        """`eq.stone-x` parses as `eq.stone - x`, so there is no way to reference it."""
        assert 'hoistable-equation' not in self._twice(tmp_path, 'stone-x')

    def test_a_mirrored_translation_is_not_a_second_copy(self, tmp_path):
        """
        `27/brakemaster` reported seven copies of what is written five times, because `cs` and `es`
        are symlinks. One equation reachable through two language paths is one equation.
        """
        block = '$$\n    x = 1\n$$ {#eq:widget:tau}\n'
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'text\n' + block},
                            'cs': {'problem.md': 'a'}})
        root = tmp_path / 'phys' / '99' / 'problems' / 'widget'
        (root / 'cs' / 'solution.md').symlink_to('../sk/solution.md')
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert 'hoistable-equation' not in ids(report)
        status = report.statuses['phys/99/problems/widget']['equations']
        assert status.detail['duplicated'] == []

    def test_two_real_files_still_count(self, tmp_path):
        block = '$$\n    x = 1\n$$ {#eq:widget:tau}\n'
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'text\n' + block},
                            'en': {'problem.md': 'a', 'solution.md': 'text\n' + block}})
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert 'hoistable-equation' in ids(report)

    def test_unnameable_is_its_own_category(self, tmp_path):
        """Identical everywhere and still unhoistable is not the same as differing."""
        block = '$$\n    x = 1\n$$ {#eq:widget:stone-x}\n'
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'text\n' + block},
                            'en': {'problem.md': 'a', 'solution.md': 'text\n' + block}})
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        status = report.statuses['phys/99/problems/widget']['equations']
        assert status.detail['unnameable'] == ['stone-x']
        assert status.detail['divergent'] == []
        assert 'not a usable key' in status.summary


class TestLabellingRule:
    """
    Náboj's rule is asymmetric: every display block in a solution carries a label, and no block
    outside a solution carries one. Both halves need a check, and each needs a case where the
    opposite file kind must stay quiet.
    """

    BLOCK = '$$\n    x = 1\n$$'
    LABELLED = '$$\n    x = 1\n$$ {#eq:widget:tau}'

    def test_an_unlabelled_block_in_a_solution_fires(self, tmp_path):
        assert 'solution-unlabelled' in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'text\n' + self.BLOCK + '\n'}}))

    def test_a_labelled_block_in_a_solution_is_quiet(self, tmp_path):
        assert 'solution-unlabelled' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'text\n' + self.LABELLED + '\n'}}))

    def test_an_unlabelled_block_in_a_statement_is_quiet(self, tmp_path):
        """The rule is asymmetric; a statement is where an unlabelled block belongs."""
        found = ids(run(tmp_path, files={
            'sk': {'problem.md': 'text\n' + self.BLOCK + '\n', 'solution.md': 'a'}}))
        assert 'solution-unlabelled' not in found
        assert 'problem-labelled' not in found

    def test_a_labelled_block_in_a_statement_fires(self, tmp_path):
        assert 'problem-labelled' in ids(run(tmp_path, files={
            'sk': {'problem.md': 'text\n' + self.LABELLED + '\n', 'solution.md': 'a'}}))

    def test_a_block_closing_a_footnote_is_exempt(self, tmp_path):
        """`$$]` closes the footnote; a label after that would sit outside it and change the page."""
        footnote = 'text^[a note\n' + self.BLOCK + '] and on\n'
        assert 'solution-unlabelled' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': footnote}}))

    def test_an_ordinary_block_is_still_required_to_have_one(self, tmp_path):
        """The exemption is for the footnote, not for anything that happens to follow a block."""
        assert 'solution-unlabelled' in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'text\n' + self.BLOCK + ' and on\n'}}))

    def test_a_mirrored_solution_is_not_a_second_unlabelled_block(self, tmp_path):
        """One block reachable through two language paths is one finding, not two."""
        make_problem(tmp_path, name='widget',
                     files={'sk': {'problem.md': 'a', 'solution.md': 'text\n' + self.BLOCK + '\n'},
                            'cs': {'problem.md': 'a'}})
        root = tmp_path / 'phys' / '99' / 'problems' / 'widget'
        (root / 'cs' / 'solution.md').symlink_to('../sk/solution.md')
        report = audit(tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
        assert len([f for f in report.findings if f.check == 'solution-unlabelled']) == 1


class TestInlineLength:
    """Long inline maths is worth hoisting; ordinary inline maths is not, and there is a lot of it."""

    def test_a_long_span_fires(self, tmp_path):
        long_maths = '$' + 'a + ' * 30 + 'b$'
        assert 'inline-long' in ids(run(tmp_path, files={
            'sk': {'problem.md': f'text {long_maths} more', 'solution.md': 'a'}}))

    def test_an_ordinary_span_is_quiet(self, tmp_path):
        """The median span is seven characters; flagging those would bury everything else."""
        assert 'inline-long' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'the speed $v = v_0 - at$ falls', 'solution.md': 'a'}}))

    def test_a_display_block_is_not_read_as_inline(self, tmp_path):
        """`$$` masked first: otherwise one long display block reads as two inline spans."""
        block = '$$\n    ' + 'a + ' * 40 + 'b\n$$ {#eq:widget:long}\n'
        assert 'inline-long' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'text\n' + block}}))


class TestWordSubscripts:
    """A word subscript is upright; a label is not a word."""

    def test_a_bare_word_subscript_fires(self, tmp_path):
        assert 'subscript-unwrapped' in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'the energy $E_{kin}$ is'}}))

    def test_a_wrapped_one_is_quiet(self, tmp_path):
        assert 'subscript-unwrapped' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'the energy $E_{\\text{kin}}$ is'}}))

    def test_capitals_are_labels_not_words(self, tmp_path):
        """`T_{KJ}` is the time from K to J; upright roman would be wrong."""
        assert 'subscript-unwrapped' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'the time $T_{KJ}$ and $c_{Kx}$'}}))

    def test_a_single_letter_is_a_symbol(self, tmp_path):
        assert 'subscript-unwrapped' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'the speed $v_0$ and $v_x$'}}))

    def test_an_identifier_in_a_template_tag_is_not_a_subscript(self, tmp_path):
        """`(§ t_up - t_down §)` names two `values:` entries. 220 of these were false positives."""
        assert 'subscript-unwrapped' not in ids(run(tmp_path, files={
            'sk': {'problem.md': 'a', 'solution.md': 'lasts $(§ t_{up} - t_{down} §)$ seconds'}}))


class TestAnswerLiteral:
    """
    An answer is the result of the problem, so it should be computed. `value_status` cannot see this:
    it reads the statement, to ask whether the numbers the problem is *given* are named.
    """

    def test_a_typed_answer_fires(self, tmp_path):
        found = ids(run(tmp_path, shared={'answer.md': '$\\qty{950}{\\kilo\\gram}$\n'}))
        assert 'answer-literal' in found

    def test_an_answer_that_reads_a_value_is_quiet(self, tmp_path):
        assert 'answer-literal' not in ids(run(tmp_path, shared={
            'answer.md': '$(§ result|f0 §)$\n'}))

    def test_a_non_numeric_answer_is_quiet(self, tmp_path):
        """226 answers are a chemical formula or a word. There is nothing to compute."""
        assert 'answer-literal' not in ids(run(tmp_path, shared={
            'answer.md': '\\ce{Hg}, \\ce{Ra}, \\ce{Li}\n'}))

    def test_an_empty_answer_is_quiet(self, tmp_path):
        assert 'answer-literal' not in ids(run(tmp_path, shared={'answer.md': '\n'}))

    def test_a_bare_integer_is_quiet(self, tmp_path):
        """`chem/01/ciment` answers `12`. Not a quantity, so not a `values:` candidate."""
        assert 'answer-literal' not in ids(run(tmp_path, shared={'answer.md': '12\n'}))

    def test_the_verdict_notices_a_typed_answer(self, tmp_path):
        """A statement fully extracted but an answer still typed is `partial`, not `ok`."""
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\n"
                "tags: ['kinematics']\nvalues:\n  v:\n    magnitude: 3\n    unit: 'metre'\n")
        report = audit(*_scope(tmp_path, meta=meta,
                              shared={'answer.md': '$\\qty{950}{\\kilo\\gram}$\n'},
                              files={'sk': {'problem.md': 'no numbers here'}}))
        status = report.statuses['phys/99/problems/widget']['values']
        assert status.state == 'partial'
        assert 'answer.md' in status.summary


def _scope(tmp_path, **kwargs):
    make_problem(tmp_path, **kwargs)
    return (tmp_path, 'naboj', 'phys/99', ['phys/99/problems/widget'])
