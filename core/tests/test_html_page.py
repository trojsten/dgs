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
from core.html import mathjax, page, texmath

# Asked of the modules rather than guessed: `texmath` shells out to two binaries and the
# MathJax engine needs node *and* what `npm ci` installs, and a guard that checks only the
# obvious half does not skip -- it lets the test die in `subprocess` instead.
needs_latex = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in texmath.REQUIRES),
    reason=f'needs {" and ".join(texmath.REQUIRES)}')
needs_node = pytest.mark.skipif(
    not mathjax.available(), reason='needs node and `npm ci`')

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


#: Two stub modules, one of each shape. **Not naboj and seminar**, deliberately: what is under
#: test here is `page.py` given a descriptor, and naming the real modules would make this suite
#: need `source/naboj/` to be checked out -- `descriptors.load_modules` knows a module only when
#: its content repository is populated, and those repositories are optional. What the real
#: descriptors say is asserted in `modules/<module>/tests/`, which skip when it is not there.
DESCRIPTORS = {
    'translated': 'label: Translated\nlanguages: true\nunits:\n'
                  "  - glob: '*'\n    targets: [problem, solution]\n",
    'flat': 'label: Flat\nunits:\n'
            "  - glob: '*'\n    targets: [problem, solution]\n",
}


@pytest.fixture(autouse=True)
def _i18n(i18n_built):
    """
    `build/core/i18n/` for the whole file. The `latex` engine loads `<lang>.tex` into every
    formula it sets, and which tests reach it is not obvious from the call -- `main()` takes
    the default engine, and `test_neither_leaves_tex_on_the_page` runs both -- so it is asked
    for once here rather than named test by test and forgotten on the next one.
    """


@pytest.fixture
def repo(tmp_path):
    """
    A checkout holding the two stub descriptors and nothing else of its own.

    `core` is symlinked rather than copied because `page.build` reads `core/html/page.css`
    relative to the working directory, as `main()` does for everything -- so a stub root has to
    be able to stand in for the real one entirely, not only for the descriptors.
    """
    root = tmp_path / 'repo'
    for name, text in DESCRIPTORS.items():
        (root / 'modules' / name).mkdir(parents=True)
        (root / 'modules' / name / 'editor.yaml').write_text(text)
        (root / 'source' / name).mkdir(parents=True)
    (root / 'core').symlink_to(pathlib.Path('core').resolve(), target_is_directory=True)
    return root


@pytest.fixture
def problem(tmp_path):
    """A built unit of a translated module: a directory per language."""
    (tmp_path / 'sk').mkdir()
    (tmp_path / 'sk' / 'problem.html').write_text(FRAGMENT)
    return tmp_path


@pytest.fixture
def flat_problem(tmp_path):
    """A built unit of a monolingual module: the fragments sit in it."""
    (tmp_path / 'problem.html').write_text(FRAGMENT)
    return tmp_path


class TestTheEngineIsAChoice:
    def test_both_engines_are_offered(self):
        assert set(page.ENGINES) == {'latex', 'mathjax'}

    def test_the_default_is_the_one_declared_once(self):
        """`core/html/__init__.py` is where it is set, so that nothing can disagree with it."""
        assert html.ENGINE in page.ENGINES

    def test_an_unknown_engine_is_refused_by_name(self, repo):
        """Quietly falling back would set the maths the wrong way and look perfectly fine."""
        with pytest.raises(ValueError, match='katex'):
            page.build(pathlib.Path('.'), 'sk', pathlib.Path('.'), engine='katex',
                       module='translated', repo_root=repo)

    @needs_latex
    def test_latex_inlines_a_measured_svg(self, problem, repo, tmp_path):
        out = page.build(problem, 'sk', tmp_path / 'out', files=('problem',),
                         engine='latex', module='translated', repo_root=repo)
        text = body(out)
        assert 'class="dgs-math"' in text
        # the baseline is measured, not guessed, and that is the whole reason for the template
        assert 'vertical-align:' in text
        assert 'mjx-container' not in text

    @needs_node
    def test_mathjax_sets_the_same_fragment_as_text(self, problem, repo, tmp_path):
        out = page.build(problem, 'sk', tmp_path / 'out', files=('problem',),
                         engine='mathjax', module='translated', repo_root=repo)
        text = body(out)
        assert 'mjx-container' in text
        assert 'class="dgs-math"' not in text

    @needs_latex
    @needs_node
    def test_neither_leaves_tex_on_the_page(self, problem, repo, tmp_path):
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
                             engine=engine, module='translated', repo_root=repo)
            text = body(out)
            for leftover in ('\\(', '\\['):
                assert leftover not in text, f'{engine} left `{leftover}` on the page'

    @needs_node
    def test_mathjax_could_not_have_done_the_expansion_itself(self, problem, repo, tmp_path):
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
                         engine='mathjax', module='translated', repo_root=repo)
        assert 'data-latex="\\qty"' in body(out)


class TestWhereTheFragmentsAre:
    """
    The descriptor says, and it says it once. A module that declares `languages: true` holds a
    directory per language inside a unit, so a fragment is `<unit>/<lang>/solution.html`; one
    that does not keeps its fragments in the unit itself. Guessing between the two by looking
    would make a half-built translated unit look like a monolingual one.

    Which real module is which is **not** asserted here -- that needs its content repository
    checked out, so it lives in `modules/naboj/tests/` and `modules/seminar/tests/`. What is
    asserted here is that `page.py` obeys whichever descriptor it is handed.
    """

    def test_a_declared_language_directory_is_read_back(self, repo):
        languages, targets = page.describe('translated', repo)
        assert languages
        assert targets == ['problem', 'solution']

    def test_a_descriptor_without_the_key_is_monolingual(self, repo):
        """Absent, not false: a module says it is translated, never that it is not."""
        assert not page.describe('flat', repo)[0]

    def test_an_unknown_module_is_refused_by_name(self, repo):
        with pytest.raises(ValueError, match='translatedd'):
            page.describe('translatedd', repo)

    def test_the_message_says_what_to_look_at(self, repo):
        """
        Both halves, because the usual cause is the second: a module is unknown when its
        descriptor is missing *or* when its content repository is not checked out, and only
        the first is anybody's first guess.
        """
        with pytest.raises(ValueError, match='is not checked out'):
            page.describe('absent', repo)

    @needs_latex
    def test_a_monolingual_unit_assembles(self, flat_problem, repo, tmp_path):
        out = page.build(flat_problem, 'sk', tmp_path / 'out', engine='latex',
                         module='flat', repo_root=repo)
        assert 'Rýchlosť' in body(out)

    @needs_latex
    def test_a_translated_unit_is_not_looked_for_beside_the_unit(self, flat_problem, repo,
                                                                 tmp_path):
        """
        The quiet case: the same directory, read as a translated module's, has nothing in it.
        If this found the fragment, the rule would be "look in both", and a unit whose language
        directory was missing would silently assemble from whatever lay beside it.
        """
        with pytest.raises(FileNotFoundError, match='sk'):
            page.build(flat_problem, 'sk', tmp_path / 'out', engine='latex',
                       module='translated', repo_root=repo)


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
    def test_the_page_is_written_and_the_gap_named(self, repo, tmp_path):
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'problem.html').write_text(
            '<p>Pozri <img src="nikde.svg" alt="" /> a <img src="tiez-nikde.svg" alt="" />.</p>')

        with pytest.raises(page.MissingPictures) as raised:
            page.build(problem, 'sk', tmp_path / 'out', engine='latex',
                       module='flat', repo_root=repo)

        assert raised.value.missing == ['nikde.svg', 'tiez-nikde.svg']
        written = raised.value.page
        assert written.is_file()
        assert body(written).count('dgs-missing') == 2
        assert 'nikde.svg' in body(written)

    @needs_latex
    def test_a_picture_that_is_there_is_copied_and_not_boxed(self, repo, tmp_path):
        """The quiet case: the same shape, with the drawing present."""
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'tam.svg').write_text(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'></svg>")
        (problem / 'problem.html').write_text('<p>Pozri <img src="tam.svg" alt="" />.</p>')

        out = page.build(problem, 'sk', tmp_path / 'out', engine='latex',
                         module='flat', repo_root=repo)
        assert 'dgs-missing' not in body(out)
        assert (tmp_path / 'out' / 'tam.svg').is_file()
        assert 'src="tam.svg"' in body(out)


class TestTheBuildStaysGreen:
    """
    `make` must not lose a round's pages over one absent drawing. `build` still raises -- the
    source really is wrong, and a caller that ignores it should not do so silently -- but the
    command line downgrades it to a warning, which is what the make rules depend on.

    These two go through `main()`, which takes no `repo_root`: the command's contract is that
    the working directory *is* the checkout, which is also how it finds `core/html/page.css`.
    So they `chdir` into the stub instead, and the stub symlinks `core` for exactly this.
    """

    @needs_latex
    def test_the_command_warns_and_succeeds(self, repo, tmp_path, capsys, monkeypatch):
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'problem.html').write_text('<p>Pozri <img src="nikde.svg" alt="" />.</p>')
        monkeypatch.chdir(repo)
        monkeypatch.setattr('sys.argv', ['page', str(problem), 'sk', str(tmp_path / 'out'),
                                         '--module', 'flat'])

        assert page.main() == 0
        printed = capsys.readouterr()
        assert 'nikde.svg' in printed.err, 'the gap has to be said out loud somewhere'
        assert (tmp_path / 'out' / 'index.html').is_file()

    @needs_latex
    def test_a_page_with_every_picture_says_nothing(self, repo, tmp_path, capsys,
                                                    monkeypatch):
        """The quiet case: no warning when there is nothing to warn about."""
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'tam.svg').write_text(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'></svg>")
        (problem / 'problem.html').write_text('<p>Pozri <img src="tam.svg" alt="" />.</p>')
        monkeypatch.chdir(repo)
        monkeypatch.setattr('sys.argv', ['page', str(problem), 'sk', str(tmp_path / 'out'),
                                         '--module', 'flat'])

        assert page.main() == 0
        assert capsys.readouterr().err == ''
