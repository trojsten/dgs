r"""
Fragments into a page, and the choice of how its maths is set.

The point of the switch is that **one pandoc build serves both engines**: `build/**.html` holds
the formula the author wrote, so the same fragments can be set by the xelatex that sets the
booklet or by MathJax, and the two are comparable because nothing upstream of the page differs.
"""
import pathlib
import shutil

import pytest

from core import html
from core.html import page

needs_latex = pytest.mark.skipif(not shutil.which('xelatex'), reason='xelatex is not installed')
needs_node = pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')

FRAGMENT = ('<p>Rýchlosť <span class="math inline">\\(\\qty{3}{\\metre\\per\\second}\\)</span> '
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
    def test_neither_leaves_a_macro_on_the_page(self, problem, tmp_path):
        r"""
        `\qty` reaches the fragment unrewritten -- that is what makes the fragment neutral --
        so each engine has to deal with it, one through siunitx itself and one through the shim.
        A page showing `\qty{3}{\metre\per\second}` is the failure this guards.
        """
        for engine in ('latex', 'mathjax'):
            out = page.build(problem, 'sk', tmp_path / engine, files=('problem',),
                             engine=engine, module='naboj')
            assert '\\qty' not in body(out), f'{engine} left the macro on the page'


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
    The call `\\protectedInput` makes in the booklet: box the hole, keep the rest of the page,
    and go red separately. One absent drawing should not cost you the other six problems of
    the round, and whoever is fixing it wants the page with the holes marked.

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
        # written anyway -- make needs `.PRECIOUS` for this to survive, and the rules say so
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
