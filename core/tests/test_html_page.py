r"""
Fragments into a page, and the choice of how its maths is set.

The point of the switch is that **one pandoc build serves both engines**: a fragment holds
plain maths -- `Convertor.expand_for_the_web` rewrote siunitx and `math.tex` on the way in --
so the same `build/**.html` can be set by the xelatex that sets the booklet or by MathJax, and
the two are comparable because nothing upstream of the page differs.
"""
import pathlib
import shutil

import pytest

from core import html
from core.html import page

needs_latex = pytest.mark.skipif(not shutil.which('xelatex'), reason='xelatex is not installed')
needs_node = pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')

#: A fragment as the convertor really writes one: the maths is plain, because
#: `expand_for_the_web` turned `$\qty{3}{\metre\per\second}$` into this before pandoc ran.
#: Written out rather than built here so the tests need no pandoc, and kept faithful by
#: `core/tests/test_convertor.py`, which is where that expansion is actually asserted.
FRAGMENT = ('<p>Rýchlosť <span class="math inline">\\(3\\ \\text{m}/\\text{s}\\)</span> '
            'a <span class="math display">\\[P = \\frac{Q}{t}\\]</span></p>\n')


def body(page_file: pathlib.Path) -> str:
    """The page without its inlined stylesheet, which names both engines' classes."""
    text = page_file.read_text()
    return text[text.index('<body>'):]


@pytest.fixture
def problem(tmp_path):
    """A built Náboj problem: a directory per language, because Náboj's text is translated."""
    (tmp_path / 'sk').mkdir()
    (tmp_path / 'sk' / 'problem.html').write_text(FRAGMENT)
    return tmp_path


@pytest.fixture
def seminar_problem(tmp_path):
    """A built seminar problem: the fragments sit in it, because seminar is monolingual."""
    (tmp_path / 'problem.html').write_text(FRAGMENT)
    return tmp_path


class TestTheEngineIsAChoice:
    def test_both_engines_are_offered(self):
        assert set(page.ENGINES) == {'latex', 'mathjax'}

    def test_the_default_is_the_one_declared_once(self):
        """`core/html/__init__.py` is where it is set, so that nothing can disagree with it."""
        assert html.ENGINE in page.ENGINES

    def test_an_unknown_engine_is_refused_by_name(self):
        """Quietly falling back would set the maths the wrong way and look perfectly fine."""
        with pytest.raises(ValueError, match='katex'):
            page.build(pathlib.Path('.'), 'sk', pathlib.Path('.'), engine='katex',
                       module='naboj')

    @needs_latex
    def test_latex_inlines_a_measured_svg(self, problem, tmp_path):
        out = page.build(problem, 'sk', tmp_path / 'out', files=('problem',),
                         engine='latex', module='naboj')
        text = body(out)
        assert 'class="dgs-math"' in text
        # the baseline is measured, not guessed, and that is the whole reason for the template
        assert 'vertical-align:' in text
        assert 'mjx-container' not in text

    @needs_node
    def test_mathjax_sets_the_same_fragment_as_text(self, problem, tmp_path):
        out = page.build(problem, 'sk', tmp_path / 'out', files=('problem',),
                         engine='mathjax', module='naboj')
        text = body(out)
        assert 'mjx-container' in text
        assert 'class="dgs-math"' not in text

    @needs_latex
    @needs_node
    def test_neither_leaves_tex_on_the_page(self, problem, tmp_path):
        r"""
        Whatever the fragment holds, a page shows typeset maths and not its source. A surviving
        `\(` or `\[` is the one symptom both engines share: the delimiters pandoc wrote are
        still there, so nothing typeset the formula between them.

        **The test is the delimiters and not the macros**, which is less obvious than it looks:
        MathJax keeps the source on every node it builds, as `data-latex="\frac{Q}{t}"`, so
        searching the markup for `\frac` finds a formula that is set perfectly. It never keeps
        a delimiter -- those are stripped before it parses.
        """
        for engine in ('latex', 'mathjax'):
            out = page.build(problem, 'sk', tmp_path / engine, files=('problem',),
                             engine=engine, module='naboj')
            text = body(out)
            for leftover in ('\\(', '\\['):
                assert leftover not in text, f'{engine} left `{leftover}` on the page'

    @needs_node
    def test_mathjax_could_not_have_done_the_expansion_itself(self, problem, tmp_path):
        r"""
        Why the expansion is in the convertor and not here. MathJax has no siunitx extension --
        none exists -- so a fragment that still said `\qty` would reach the page as the four red
        letters MathJax prints for an unknown macro. That is not a hypothetical: it is what this
        very test showed when the fixture above still carried an unexpanded `\qty`, with the
        `latex` engine passing beside it because xelatex simply loads siunitx.
        """
        (problem / 'sk' / 'problem.html').write_text(
            '<p><span class="math inline">\\(\\qty{3}{\\metre\\per\\second}\\)</span></p>\n')
        out = page.build(problem, 'sk', tmp_path / 'raw', files=('problem',),
                         engine='mathjax', module='naboj')
        assert 'data-latex="\\qty"' in body(out)


class TestWhereTheFragmentsAre:
    """
    The module says, and it says it once: `languages: true` in `modules/naboj/editor.yaml`.
    Náboj's text is translated, so a problem holds a directory per language; **seminar is
    monolingual** -- one language, not one of several that happens to be checked out -- so its
    fragments sit in the problem directory. Guessing between the two by looking would make a
    half-built Náboj problem look like a seminar one.
    """

    def test_naboj_has_a_language_directory(self):
        languages, targets = page.describe('naboj')
        assert languages
        assert targets[:2] == ['problem', 'problem-extra']

    def test_seminar_has_not(self):
        languages, targets = page.describe('seminar')
        assert not languages
        assert targets == ['problem', 'solution']

    def test_an_unknown_module_is_refused_by_name(self):
        with pytest.raises(ValueError, match='nabojj'):
            page.describe('nabojj')

    @needs_latex
    def test_a_monolingual_unit_assembles(self, seminar_problem, tmp_path):
        out = page.build(seminar_problem, 'sk', tmp_path / 'out', engine='latex',
                         module='seminar')
        assert 'Rýchlosť' in body(out)

    @needs_latex
    def test_a_translated_unit_is_not_looked_for_beside_the_problem(self, seminar_problem,
                                                                    tmp_path):
        """
        The quiet case: the same directory, read as Náboj's, has nothing in it. If this found
        the fragment, the rule would be "look in both", and a Náboj problem whose language
        directory was missing would silently assemble from whatever lay beside it.
        """
        with pytest.raises(FileNotFoundError, match='sk'):
            page.build(seminar_problem, 'sk', tmp_path / 'out', engine='latex', module='naboj')


class TestAMissingPictureIsBoxed:
    """
    Box the hole, keep the rest of the page, and **do not fail the build**. An absent drawing
    is not a missing word: a word goes wrong in one language and nowhere else, while a hole in
    a figure is visible to anyone who opens the page -- and failing would cost a whole round
    its pages for one hole in one problem.

    `FKS/42/1/1/01` is the live case -- its solution names four drawings and the directory
    holds two.
    """

    @needs_latex
    def test_the_page_is_written_and_the_gap_named(self, tmp_path):
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'problem.html').write_text(
            '<p>Pozri <img src="nikde.svg" alt="" /> a <img src="tiez-nikde.svg" alt="" />.</p>')

        with pytest.raises(page.MissingPictures) as raised:
            page.build(problem, 'sk', tmp_path / 'out', engine='latex', module='seminar')

        assert raised.value.missing == ['nikde.svg', 'tiez-nikde.svg']
        written = raised.value.page
        assert written.is_file()
        assert body(written).count('dgs-missing') == 2
        assert 'nikde.svg' in body(written)

    @needs_latex
    def test_a_picture_that_is_there_is_copied_and_not_boxed(self, tmp_path):
        """The quiet case: the same shape, with the drawing present."""
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'tam.svg').write_text(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'></svg>")
        (problem / 'problem.html').write_text('<p>Pozri <img src="tam.svg" alt="" />.</p>')

        out = page.build(problem, 'sk', tmp_path / 'out', engine='latex', module='seminar')
        assert 'dgs-missing' not in body(out)
        assert (tmp_path / 'out' / 'tam.svg').is_file()
        assert 'src="tam.svg"' in body(out)


class TestTheBuildStaysGreen:
    """
    `make` must not lose a round's pages over one absent drawing. `build` still raises -- the
    source really is wrong, and a caller that ignores it should not do so silently -- but the
    command line downgrades it to a warning, which is what the make rules depend on.
    """

    @needs_latex
    def test_the_command_warns_and_succeeds(self, tmp_path, capsys, monkeypatch):
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'problem.html').write_text('<p>Pozri <img src="nikde.svg" alt="" />.</p>')
        monkeypatch.setattr('sys.argv', ['page', str(problem), 'sk', str(tmp_path / 'out'),
                                         '--module', 'seminar'])

        assert page.main() == 0
        printed = capsys.readouterr()
        assert 'nikde.svg' in printed.err, 'the gap has to be said out loud somewhere'
        assert (tmp_path / 'out' / 'index.html').is_file()

    @needs_latex
    def test_a_page_with_every_picture_says_nothing(self, tmp_path, capsys, monkeypatch):
        """The quiet case: no warning when there is nothing to warn about."""
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'tam.svg').write_text(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'></svg>")
        (problem / 'problem.html').write_text('<p>Pozri <img src="tam.svg" alt="" />.</p>')
        monkeypatch.setattr('sys.argv', ['page', str(problem), 'sk', str(tmp_path / 'out'),
                                         '--module', 'seminar'])

        assert page.main() == 0
        assert capsys.readouterr().err == ''
