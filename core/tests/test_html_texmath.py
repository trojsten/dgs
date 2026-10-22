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
    """

    def test_the_package_lists_are_identical(self):
        assert packages(MATHPAGE) == packages(STANDALONE), \
            'mathpage.jtex and standalone.jtex have drifted apart'

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
