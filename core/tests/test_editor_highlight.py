"""
The editor's syntax highlighter, tested through its own JavaScript.

`tools/editor/static/highlight.js` is pure -- text and a mode name in, HTML out, no DOM -- so the
whole file loads under QuickJS and these test the shipped code rather than a Python transcription
of it. That matters more here than it looks: the rules are regexes, and a regex that quietly
mis-tokenises is exactly the kind of defect nobody notices by glancing at a coloured pane.
"""
import html as htmllib
import pathlib
import re

import pytest

quickjs = pytest.importorskip('quickjs')

HIGHLIGHT_JS = pathlib.Path('tools/editor/static/highlight.js')
SPAN = re.compile(r'<span class="([\w-]+)">(.*?)</span>', re.DOTALL)


@pytest.fixture(scope='module')
def highlight():
    """`highlight(text, mode)` as the browser would call it."""
    context = quickjs.Context()
    context.eval(HIGHLIGHT_JS.read_text())
    return context.eval('highlight')


@pytest.fixture(scope='module')
def tokens(highlight):
    """Every highlighted span as (class, text), with the HTML escaping undone."""
    def call(text, mode):
        return [(cls, htmllib.unescape(body))
                for cls, body in SPAN.findall(highlight(text, mode))]
    return call


@pytest.fixture(scope='module')
def plain(highlight):
    """What the pane displays, with the markup stripped back off."""
    def call(text, mode):
        return htmllib.unescape(re.sub(r'</?span[^>]*>', '', highlight(text, mode)))
    return call


class TestNothingIsEverLost:
    """
    The property the whole tokeniser has to keep: colouring text may not change it.

    `highlight` claims ranges and carves overlaps out of them, which is exactly the kind of
    index arithmetic that drops or repeats a character when a rule is added.
    """

    #: A file of each mode's own kind. Mixing them is not enough: a `.tex` holds no `(§ … §)`,
    #: so running `dgs-md` over one never overlaps a Jinja tag with a maths span -- which is
    #: precisely the case the carving arithmetic can get wrong. Found by mutating that line and
    #: watching this test stay green.
    CORPUS = [
        ('dgs-md', 'source/naboj/phys/29/problems/bolognese/sk/solution.md'),
        ('dgs-tex', 'build/naboj/phys/29/problems/brake-fade/sk/solution.tex'),
        ('dgs-yaml', 'source/naboj/phys/29/problems/bolognese/meta.yaml'),
        ('dgs-md', 'build/naboj/phys/29/problems/brake-fade/sk/solution.tex'),
        ('dgs-tex', 'source/naboj/phys/29/problems/bolognese/sk/solution.md'),
    ]

    @pytest.mark.parametrize('mode,path', CORPUS, ids=[f'{m}:{pathlib.Path(p).suffix}'
                                                       for m, p in CORPUS])
    def test_a_real_file_survives_being_highlighted(self, plain, mode, path):
        source = pathlib.Path(path)
        if not source.is_file():
            pytest.skip(f'{path} is not present to test against')
        text = source.read_text()
        assert plain(text, mode) == text

    def test_a_tag_nested_inside_maths_splits_it_in_two(self, tokens):
        """
        The carving arithmetic, asserted on the spans rather than on the text.

        Losing a claim does *not* lose text -- `highlight` emits whatever it has not claimed
        verbatim -- so the property above cannot see it, and mutating either half of the carve
        left that test green. What a broken carve costs is colour: the maths span either side of
        the tag. Both halves have to survive, exactly.
        """
        assert tokens('$x = (§ r §)$', 'dgs-md') == [
            ('tok-math', '$x = '),          # before the tag
            ('tok-jinja', '(§ r §)'),       # the higher-priority claim
            ('tok-math', '$'),              # and after it
        ]

    def test_a_command_inside_maths_splits_it_the_same_way(self, tokens):
        """The same carve, in the mode where the priorities are the other way round."""
        assert tokens(r'\(a \frac b\)', 'dgs-tex') == [
            ('tok-math', r'\(a '),
            ('tok-cmd', r'\frac'),
            ('tok-math', r' b\)'),
        ]

    @pytest.mark.parametrize('mode', ['dgs-md', 'dgs-tex', 'dgs-yaml'])
    def test_an_unknown_mode_changes_nothing_either(self, plain, highlight, mode):
        text = r'\begin{x} $a$ % hi'
        assert plain(text, 'no-such-mode') == text
        assert '<span' not in highlight(text, 'no-such-mode')

    def test_markup_in_the_source_is_escaped(self, highlight):
        """A problem statement may contain `<` and `&`; neither may reach the pane as markup."""
        out = highlight(r'a < b & c > d \emph{<script>}', 'dgs-tex')
        assert '&lt;' in out and '&amp;' in out
        assert '<script>' not in out


class TestTheTexMode:
    def test_a_comment_runs_to_the_end_of_the_line(self, tokens):
        got = tokens('x % a comment\ny', 'dgs-tex')
        assert ('tok-comment', '% a comment') in got

    def test_an_escaped_percent_is_not_a_comment(self, tokens):
        r"""`\%` is a literal per cent sign -- a very common thing in these sources."""
        got = tokens(r'50\% of it', 'dgs-tex')
        assert not [t for t in got if t[0] == 'tok-comment']

    def test_an_environment_is_marked_as_structure(self, tokens):
        got = tokens(r'\begin{itemize}\item a\end{itemize}', 'dgs-tex')
        assert ('tok-heading', r'\begin{itemize}') in got
        assert ('tok-heading', r'\end{itemize}') in got

    def test_pandoc_maths_delimiters_are_recognised(self, tokens):
        r"""pandoc emits `\(…\)` and `\[…\]`, not `$…$` -- the TeX tab shows pandoc's output."""
        assert any(cls == 'tok-math' for cls, _ in tokens(r'a \(x + y\) b', 'dgs-tex'))
        assert any(cls == 'tok-math' for cls, _ in tokens(r'a \[x + y\] b', 'dgs-tex'))

    def test_dollar_maths_still_works_for_hand_written_tex(self, tokens):
        assert any(cls == 'tok-math' for cls, _ in tokens('a $x+y$ b', 'dgs-tex'))

    def test_a_command_inside_maths_is_still_a_command(self, tokens):
        """
        The deliberate inversion, the opposite way round from `dgs-md`: generated TeX is mostly
        `\\qty{…}{…}` *inside* maths, so a maths span that swallowed its commands would be one
        flat colour. Commands are claimed first and the delimiters keep what is left.
        """
        got = tokens(r'\(F = \frac{1}{2} m v^2\)', 'dgs-tex')
        assert ('tok-cmd', r'\frac') in got
        assert any(cls == 'tok-math' for cls, _ in got)

    def test_a_command_in_a_comment_is_not_highlighted_separately(self, tokens):
        """Comments outrank everything: the line is commentary, not code."""
        got = tokens(r'% see \frac and \(x\)', 'dgs-tex')
        assert [t for t in got if t[0] == 'tok-cmd'] == []

    def test_starred_commands_are_one_token(self, tokens):
        assert ('tok-cmd', r'\vspace*') in tokens(r'\vspace*{1cm}', 'dgs-tex')

    def test_numbers_are_marked(self, tokens):
        assert ('tok-number', '42') in tokens(r'\qty{42}{\metre}', 'dgs-tex')


class TestTheMarkdownModeIsUnchanged:
    """`dgs-tex` was added beside these; a shared tokeniser makes that worth pinning."""

    def test_a_jinja_tag_wins_inside_maths(self, tokens):
        """The priority `dgs-md` wants, and the reason `dgs-tex` inverting it is worth a test."""
        got = tokens('$x = (§ result §)$', 'dgs-md')
        assert ('tok-jinja', '(§ result §)') in got

    def test_a_display_block_is_maths(self, tokens):
        assert any(cls == 'tok-math' for cls, _ in tokens('$$\n  a = b\n$$', 'dgs-md'))

    def test_a_label_is_its_own_token(self, tokens):
        assert ('tok-label', '{#eq:x:y}') in tokens('$$a$$ {#eq:x:y}', 'dgs-md')
