"""
`/api/evaluate`: what a fragment of template comes out as, for the editor's hover.

The point of the endpoint is that it answers for the *buffer*, not for the file -- somebody
typing a `derived:` expression wants to know what it gives before they save it -- and that it
answers the same as a build would, because a popup that disagrees with the booklet is worse than
no popup. Both of those are what is tested here.

Against a real problem rather than a fixture: the thing worth asserting is that this and
`make` agree, and a hand-built meta would only ever agree with itself.
"""
import pathlib
import sys

import pytest

EDITOR = pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'editor'
sys.path.insert(0, str(EDITOR))

import app as editor                                  # noqa: E402

UNIT = 'phys/29/problems/speedy-reflection'
META = pathlib.Path('source/naboj/phys/29/problems/speedy-reflection/meta.yaml')

pytestmark = pytest.mark.skipif(not META.is_file(),
                                reason='source/naboj/phys is not checked out')

#: What Náboj's schema demands of any meta, so a test writing its own can say only the part it is
#: about. A buffer missing these is genuinely invalid and the endpoint is right to say so -- see
#: `TestFailuresAreTheAnswerToo` -- which is exactly why it cannot be left out here by accident.
PREAMBLE = "authors:\n  idea: []\ntags: []\n"


@pytest.fixture
def ask():
    """`POST /api/evaluate` for this problem, returning the parsed body."""
    client = editor.app.test_client()

    def call(fragments, *, meta=None, target='solution', lang='sk', unit=UNIT):
        response = client.post('/api/evaluate', json={
            'module': 'naboj', 'unit': unit, 'lang': lang, 'target': target,
            'meta_yaml': META.read_text() if meta is None else meta,
            'fragments': fragments,
        })
        return response.get_json()
    return call


@pytest.fixture
def one(ask):
    """The single result of a single fragment."""
    return lambda fragment, **kwargs: ask([fragment], **kwargs)['results'][0]


class TestWhatAFragmentComesOutAs:
    def test_an_equation_is_its_own_latex(self, one):
        assert one('(§ eq.snell §)')['text'] == r'n \cdot \sin \alpha = 1 \cdot \sin \ang{90}'

    def test_inl_wraps_it_the_way_the_filter_does(self, one):
        assert one('(§ eq.snell|inl §)')['text'].startswith('$')
        assert one('(§ eq.snell|inl §)')['text'].endswith('$')

    def test_a_derived_quantity_is_a_number(self, one):
        text = one('(§ result_approx|ef2 §)')['text']
        assert text.startswith('a = \\qty{') and '\\metre\\per\\second\\squared' in text

    def test_a_constant_resolves(self, one):
        assert one('(§ const.refraction_water.eq §)')['text'].startswith('n_{\\ce{H2O}}')

    def test_a_word_follows_the_language(self, one):
        assert one('(§ words.effective §)', lang='sk')['text'] \
            != one('(§ words.effective §)', lang='en')['text']

    def test_a_display_comes_back_with_its_delimiters_and_label(self, one):
        text = one('(§ eq.result|disp(".") §)')['text']
        assert text.startswith('$$') and '{#eq:speedy-reflection:result}' in text

    def test_a_statement_does_not_label_its_equations(self, one):
        """
        `equation_numbering` is the module's, and it is read here the same way the renderer reads
        it -- so the popup shows a problem's display without the `{#eq:}` a solution's would have.
        """
        assert '{#eq:' not in one('(§ eq.result|disp(".") §)', target='problem')['text']
        assert '{#eq:' in one('(§ eq.result|disp(".") §)', target='solution')['text']


class TestItAnswersForTheBuffer:
    def test_an_unsaved_value_is_the_one_used(self, one):
        meta = PREAMBLE + 'values:\n  v:\n    magnitude: 42\n    unit: m\n'
        assert '42' in one('(§ v §)', meta=meta)['text']

    def test_an_unsaved_equation_is_the_one_shown(self, one):
        meta = PREAMBLE + "eq:\n  snell: 'nothing like the real one'\n"
        assert one('(§ eq.snell §)', meta=meta)['text'] == 'nothing like the real one'

    def test_nothing_is_written(self, one):
        before = META.read_text()
        one('(§ v §)', meta=PREAMBLE + 'values:\n  v:\n    magnitude: 1\n    unit: m\n')
        assert META.read_text() == before


class TestFailuresAreTheAnswerToo:
    """
    A fragment that cannot be rendered is reported, not hidden. Somebody hovering a tag that does
    not work is exactly who most needs telling, and the alternative -- an empty popup -- reads as
    "nothing to say about this" rather than "this is broken".
    """

    def test_an_unknown_name_fails_that_fragment_alone(self, ask):
        body = ask(['(§ eq.snell §)', '(§ nonsense §)'])
        assert body['ok']
        assert body['results'][0]['ok']
        assert not body['results'][1]['ok']
        assert 'nonsense' in body['results'][1]['error']

    def test_a_broken_derived_expression_fails_the_whole_request(self, ask):
        """One bad `derived:` entry and there is no context at all, so it is the one answer."""
        body = ask(['(§ x §)'], meta=PREAMBLE + 'derived:\n  x: "1 / 0"\n')
        assert not body['ok']
        assert 'x' in body['error']

    def test_unparseable_yaml_says_so(self, ask):
        body = ask(['(§ x §)'], meta='values: [unclosed\n')

    def test_a_meta_the_schema_refuses_is_refused(self, ask):
        """Strict on purpose: `make` would refuse it too, and a popup that quietly accepted a
        meta the build will not is the one disagreement this endpoint exists to prevent."""
        body = ask(['(§ x §)'], meta='values:\n  x:\n    magnitude: 1\n')
        assert not body['ok'] and body['error']
        assert not body['ok'] and body['error']

    def test_an_error_carries_no_terminal_colour(self, ask):
        """The renderer colours its own messages, and an escape sequence in a tooltip is noise."""
        assert '\x1b' not in ask(['(§ nonsense §)'])['results'][0]['error']

    def test_an_unknown_unit_is_a_bad_request(self):
        client = editor.app.test_client()
        response = client.post('/api/evaluate', json={
            'module': 'naboj', 'unit': 'phys/29/problems/not-a-problem',
            'lang': 'sk', 'target': 'solution', 'fragments': []})
        assert response.status_code == 400

    def test_fragments_must_be_strings(self, ask):
        client = editor.app.test_client()
        response = client.post('/api/evaluate', json={
            'module': 'naboj', 'unit': UNIT, 'lang': 'sk', 'target': 'solution',
            'fragments': [{'not': 'a string'}]})
        assert response.status_code == 400


class TestItAgreesWithTheRenderer:
    """
    The whole justification for the endpoint existing: it shares `build_render_context` and
    `render_twice` with the build, so it cannot answer differently. Asserted rather than assumed,
    because "they share a function" stops being true the moment somebody inlines one of them.
    """

    FRAGMENTS = ['(§ eq.snell|inl §)', '(§ result_approx|ef2 §)', '(§ eq.result|disp(".") §)']

    def test_it_matches_what_the_renderer_would_write(self, ask):
        from core.builder.renderer import build_render_context, render_twice
        from core.builder.jinja import MarkdownJinjaRenderer
        from modules.naboj.builder.renderer import CLIInterface

        meta = CLIInterface.context_cls(str(META), META).add(id=META.parent.name)
        meta.validate()
        context = build_render_context(meta, 'sk', root=META.parent,
                                       labelled=CLIInterface.equation_numbering['solution.md'])
        renderer = MarkdownJinjaRenderer(root=META.parent)

        got = ask(self.FRAGMENTS)['results']
        for fragment, result in zip(self.FRAGMENTS, got):
            assert result['text'] == render_twice(fragment, context.data,
                                                  renderer=renderer).strip()
