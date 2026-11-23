r"""
Maths on the web, set by the LaTeX that sets the booklet.

Two halves, and only the first needs xelatex. The arithmetic that puts a formula on the
reader's baseline is pure, and it is where the bugs were: an image does not know where its
baseline is, and getting that wrong drops every inline formula onto a line of its own.
"""
import pathlib
import re
import shutil

import pytest

from core.html import texmath

STANDALONE = pathlib.Path('core/templates/standalone.jtex')
MATHPAGE = pathlib.Path('core/templates/mathpage.jtex')

# Asked of the module, not guessed: it shells out to `dvisvgm` as well, and CI had TeX
# without it -- the test died in `subprocess` where it should have skipped.
needs_latex = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in texmath.REQUIRES),
    reason=f'needs {" and ".join(texmath.REQUIRES)}')


def packages(template: pathlib.Path) -> list[str]:
    """Every `\\RequirePackage` and `\\input{core/...}` line, in order, comments and all."""
    return [line.rstrip() for line in template.read_text().splitlines()
            if line.startswith((r'\RequirePackage', r'\input{core'))]


class TestTheTwoTemplatesAgree:
    """
    `mathpage.jtex` exists to set the *same* maths as `standalone.jtex`, in the same font with
    the same macros. A package added to one and not the other is how the web and the print
    maths start to differ, and the difference is exactly the kind nobody notices.

    **They cannot drift any more, because there is one list.** The 73 lines they shared are
    `core/templates/standalone-preamble.jtex` and each includes it. So the old assertion --
    that the two package lists are equal -- is now trivially true of two empty lists, which is
    not a test. What is worth pinning is that neither has started keeping packages of its own
    again, and that the shared file is really where they live.
    """

    SHARED = pathlib.Path('core/templates/standalone-preamble.jtex')

    def test_both_include_the_shared_preamble(self):
        for template in (MATHPAGE, STANDALONE):
            assert "(@ include 'standalone-preamble.jtex' @)" in template.read_text(), \
                f'{template.name} no longer takes the shared preamble'

    def test_neither_keeps_packages_of_its_own(self):
        """
        The one that would fire. A package added to `mathpage.jtex` rather than to the shared
        file is exactly the drift this arrangement removed, and it would look perfectly
        reasonable in a diff.
        """
        assert packages(MATHPAGE) == packages(STANDALONE) == [], \
            'a package has been added to one template instead of to the shared preamble'

    def test_the_shared_preamble_is_where_they_are(self):
        assert len(packages(self.SHARED)) >= 20

    def test_the_measuring_environment_is_there(self):
        """Without `multi=`, one xelatex run would give one page and the whole batch would be lost."""
        text = MATHPAGE.read_text()
        assert 'multi=dgsmath' in text
        assert r'\newenvironment{dgsmath}' in text
        assert 'DGSMETRIC' in text


class TestTheDelimitersComeOff:
    """pandoc hands over `\\(…\\)` and `\\[…\\]`; LaTeX wants what is between them."""

    @pytest.mark.parametrize('body, expected', [
        (r'\(a = b\)', 'a = b'),
        (r'\[a = b\]', 'a = b'),
        (r'\(\qty{3}{\metre}\)', r'\qty{3}{\metre}'),
        ('a &lt; b', 'a < b'),                          # pandoc escapes inside the span
    ])
    def test_it_strips_what_pandoc_wrote(self, body, expected):
        assert texmath.strip(body) == expected

    def test_a_fragment_with_no_delimiters_is_left_alone(self):
        """The quiet case: nothing to strip is not an error, and must not eat two characters."""
        assert texmath.strip('a = b') == 'a = b'
        assert texmath.strip(r'\langle x \rangle') == r'\langle x \rangle'


class TestTheBaseline:
    """
    `height` is the whole box and `vertical-align` is how far it hangs below the baseline, both
    in `ex`, which is MathJax's scheme and the reason a formula scales with the text around it.
    """

    def test_an_inline_formula_hangs_by_its_depth(self):
        # a box 8pt tall and 2pt deep in a font whose x-height is 4pt
        out = texmath.inline_svg("<svg foo='1'></svg>", 8.0, 2.0, 4.0, display=False)
        assert 'height: 2.500ex' in out                 # (8 + 2) / 4
        assert 'vertical-align: -0.500ex' in out        # -2 / 4

    def test_a_display_does_not_hang(self):
        """A display is its own block, so shifting it off the baseline would only move the line."""
        out = texmath.inline_svg("<svg foo='1'></svg>", 8.0, 2.0, 4.0, display=True)
        assert 'vertical-align' not in out
        assert out.startswith('<span class="dgs-math-display">')

    def test_the_absolute_size_is_dropped(self):
        """
        dvisvgm writes `width` and `height` in points. Left on, they would override the `ex`
        and the formula would stay one size while the page's type changed around it.
        """
        svg = "<svg version='1.1' width='21.07pt' height='7.38pt' viewBox='0 -7.38 21.07 7.38'>"
        out = texmath.inline_svg(svg + '</svg>', 8.0, 2.0, 4.0, display=False)
        assert "width='21.07pt'" not in out and "height='7.38pt'" not in out
        assert "viewBox='0 -7.38 21.07 7.38'" in out

    def test_the_colour_is_the_page_s(self):
        """`--no-fonts` leaves bare paths, so the formula takes the prose's own ink."""
        out = texmath.inline_svg("<svg foo='1'></svg>", 8.0, 2.0, 4.0, display=False)
        assert 'fill="currentColor"' in out

    def test_a_rule_takes_the_page_s_ink(self):
        """
        A glyph is a filled path with no `fill` of its own; a **rule** is not. A fraction bar, a
        `\\sqrt` overbar and an `\\hline` are stroked paths dvisvgm gives an explicit
        `stroke='#000'`, which overrides anything inherited -- so a fraction bar would keep
        its own colour while the digits took the page's.
        """
        svg = ("<svg><path d='M1 7H9' stroke='#000' fill='none' stroke-width='.44'/></svg>")
        out = texmath.inline_svg(svg, 8.0, 2.0, 4.0, display=False)
        assert "stroke='currentColor'" in out and "stroke='#000'" not in out

    def test_a_colour_the_drawing_chose_is_left_alone(self):
        """The quiet case: only the default ink is rewritten, so a red bond stays red."""
        svg = "<svg><path d='M1 7H9' stroke='#f00'/><path d='M2 8H9' fill='#3366cc'/></svg>"
        out = texmath.inline_svg(svg, 8.0, 2.0, 4.0, display=False)
        assert "stroke='#f00'" in out and "fill='#3366cc'" in out

    def test_a_viewbox_with_the_word_height_in_it_survives(self):
        """The quiet case: the attributes are stripped from the opening tag and nowhere else."""
        svg = "<svg width='1pt' height='2pt'><desc>height='9pt'</desc></svg>"
        assert "height='9pt'" in texmath.inline_svg(svg, 8.0, 2.0, 4.0, display=False)


class TestTheCacheKey:
    """Two formulas that set differently must not share a name."""

    def test_inline_and_display_differ(self):
        assert texmath.digest('x', 'sk', False) != texmath.digest('x', 'sk', True)

    def test_the_language_is_in_it(self):
        """`babel` is loaded, so the same `\\text{}` can set differently per language."""
        assert texmath.digest('x', 'sk', False) != texmath.digest('x', 'en', False)

    def test_the_same_formula_is_the_same_name(self):
        """The quiet case, and the point of the cache: an unchanged formula is not re-rendered."""
        assert texmath.digest('x', 'sk', False) == texmath.digest('x', 'sk', False)

    def test_the_macros_that_set_it_are_in_it(self, tmp_path, monkeypatch):
        """
        The half that was missing, and the only defect in this repository where a **correct**
        rebuild produced wrong output.

        `tools/ninja/generate.py` has always declared `math.tex` and its neighbours as implicit
        inputs of every page edge, so editing one rebuilt all fifteen thousand pages. The key
        was `VERSION` plus the formula, so every one of those rebuilds reassembled the page out
        of SVGs typeset by the *previous* macros. Nothing could see it: a stale cache entry and
        a fresh one are the same bytes on disk, and the build was green either way.
        """
        from core.html import preamble

        # A copy in `tmp_path`, never the tracked file. Writing to `core/latex/math.tex` and
        # restoring it in a `finally` worked until it did not: a `finally` does not survive
        # SIGKILL or a parallel run, and these would have been the only tests in the suite that
        # edit the source tree.
        copied = tmp_path / 'math.tex'
        copied.write_text((preamble.ROOT / 'core/latex/math.tex').read_text())
        # The real list, captured **before** patching: reading `preamble.inputs` inside the
        # replacement would read the replacement.
        stand_in = (*[p for p in preamble.inputs() if not p.endswith('math.tex')], str(copied))
        monkeypatch.setattr(preamble, 'inputs', lambda: stand_in)
        before = texmath.digest(r'\frac{1}{2}mv^2', 'sk', False)
        copied.write_text(copied.read_text() + '\n% a macro somebody redefined\n')
        assert texmath.digest(r'\frac{1}{2}mv^2', 'sk', False) != before

    def test_it_notices_without_being_restarted(self, tmp_path, monkeypatch):
        """
        Keyed on the inputs' mtimes rather than cached once per process, because the editor
        serves for hours. A `functools.cache` on the file contents would have reproduced the
        `VERSION` trap exactly: correct for a build, silently stale for anybody editing
        `math.tex` with the editor open.
        """
        from core.html import preamble

        # Again a copy: the point is that the *key moves when a watched file does*, and a file
        # in `tmp_path` is as watched as any other once `inputs()` names it.
        copied = tmp_path / 'symbols.tex'
        copied.write_text('% nothing yet\n')
        monkeypatch.setattr(preamble, 'inputs', lambda: (str(copied),))
        before = preamble.digest()
        copied.write_text('% edited while this process is live\n')
        assert preamble.digest() != before              # no cache_clear anywhere
        copied.write_text('% nothing yet\n')
        assert preamble.digest() == before


class TestWhatThePreambleIsMadeOf:
    """
    `core/html/preamble.py` reads the list off the template instead of restating it, which is
    what retired both the hand-written tuple in the graph generator and the hand-bumped
    `VERSION` here.
    """

    def test_it_follows_the_include_to_find_them(self):
        """
        The `\\input` lines live in the shared preamble now, so a scan of `mathpage.jtex` alone
        would find **none** of them and the cache key would stop covering `math.tex` again --
        the Wave 2 defect, reintroduced by the Wave 3 tidy-up. This is what stops that.
        """
        from core.html import preamble
        found = list(preamble.inputs())
        assert found[0] == 'core/templates/mathpage.jtex'
        assert 'core/templates/standalone-preamble.jtex' in found
        shared = pathlib.Path('core/templates/standalone-preamble.jtex').read_text()
        for path in preamble.RE_INPUT.findall(shared):
            if not path.startswith('build/'):
                assert path in found, f'{path} is inputted by the preamble and is not hashed'
        assert 'core/latex/math.tex' in found

    def test_the_generated_i18n_table_is_not_one_of_them(self):
        r"""
        The quiet case. The template's last `\input` is `build/core/i18n/(* lang *).tex` -- a
        generated file, named through a Jinja tag, one per language. The language is already in
        the cache key, and hashing a path that does not exist until something builds it would
        make this fail on a fresh clone.
        """
        from core.html import preamble
        assert not any(path.startswith('build/') for path in preamble.inputs())
        assert not any('(*' in path for path in preamble.inputs())

    def test_every_input_is_a_file_that_exists(self):
        from core.html import preamble
        missing = [path for path in preamble.inputs() if not pathlib.Path(path).is_file()]
        assert not missing, f'the maths preamble names files that are not there: {missing}'


class TestTypesetting:
    def test_a_fragment_with_no_maths_is_returned_as_it_was(self):
        """The quiet case, and it must not start xelatex to discover there is nothing to do."""
        plain = ['<p>No maths here at all.</p>', '<p>Nor here.</p>']
        assert texmath.typeset(plain, 'sk') == plain

    @needs_latex
    def test_it_sets_siunitx_and_math_tex_for_real(self, i18n_built, tmp_path, monkeypatch):
        """
        The fires case, and the reason for the whole module: `\\qty` and `\\FDiff` reach xelatex
        unrewritten, so what comes back is the booklet's own output -- including the Slovak
        decimal comma, which no shim of ours ever produced.
        """
        monkeypatch.setattr(texmath, 'CACHE', tmp_path)         # not the build's cache
        out, = texmath.typeset(
            [(r'<p><span class="math inline">\(\qty{4.506}{\hour}\)</span> '
             r'and <span class="math display">\[\FDiff{t}\]</span></p>')], 'sk')
        assert '<svg' in out and 'dgs-math-display' in out
        assert not re.search(r'\\[a-zA-Z]+', out), 'a macro reached the page unexpanded'
