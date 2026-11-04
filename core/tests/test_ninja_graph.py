r"""
The HTML half of the generated graph, over the helpers that write it.

These are the pure parts of `tools/ninja/generate.py` -- the ones that decide *which* edge a
file takes -- so they can be exercised with a `Writer` over a `StringIO` and no source tree,
which is what `core/tests/` is allowed to assume. The edges themselves are checked by building
a volume and diffing against make; what is pinned here is the shape, because every one of these
choices has a wrong answer that produces a plausible-looking graph:

- a fragment that goes to only one writer, so the web is built from something else than print;
- a web picture that is drawn or converted the wrong way, which is a hairline turned into a
  heavy frame (`dvisvgm`) or three blank figures (a `.gp` setting its own terminal);
- a page that looks for its fragments one directory off, which for Náboj is the difference
  between a language and the problem above it.
"""
import io
import pathlib

import pytest

from tools.ninja.generate import (
    _beside,
    _fragment,
    _instagram,
    _page,
    _picture_svg,
    _standalone,
)
from tools.ninja.writer import Writer

REPO = pathlib.Path('/repo')
META = REPO / 'source/naboj/phys/29/problems/drenched/meta.yaml'


@pytest.fixture
def writer():
    return Writer(io.StringIO())


def written(writer) -> str:
    return writer.out.getvalue()


class TestAFragmentGoesToBothWriters:
    """
    One Jinja stage, two writers. A second route to the web would be a second chance for the
    page and the booklet to disagree about what the problem says, which is the whole reason the
    `.html` hangs off the same `render/…md` as the `.tex`.
    """

    def test_it_returns_the_tex_and_the_html(self, writer):
        tex, html = _fragment(writer.build, 'source/naboj/x/sk/solution.md',
                              'naboj/x/sk/solution', 'sk', META, REPO)
        assert tex == 'build/naboj/x/sk/solution.tex'
        assert html == 'build/naboj/x/sk/solution.html'

    def test_both_are_made_from_the_one_rendered_markdown(self, writer):
        _fragment(writer.build, 'source/naboj/x/sk/solution.md', 'naboj/x/sk/solution',
                  'sk', META, REPO)
        text = written(writer)
        assert 'build/naboj/x/sk/solution.tex: pandoc_tex render/naboj/x/sk/solution.md' in text
        assert 'build/naboj/x/sk/solution.html: pandoc_html render/naboj/x/sk/solution.md' in text

    def test_the_html_waits_for_the_crossref_table_too(self, writer):
        """pandoc reads `build/core/i18n/<lang>.yaml` whichever writer it is running."""
        _fragment(writer.build, 'source/naboj/x/sk/solution.md', 'naboj/x/sk/solution',
                  'sk', META, REPO)
        line = next(l for l in written(writer).splitlines() if 'pandoc_html' in l)
        assert '| build/core/i18n/sk.yaml' in line


class TestAWebPictureIsTheBookletsPicture:
    """
    There is no separate web drawing: every route goes through the artefact the booklet prints,
    except the two that would cost a conversion to arrive where they started.
    """

    def test_a_hand_drawn_svg_is_copied(self, writer):
        """Round-tripping it through a PDF would be two conversions for nothing."""
        assert _picture_svg(writer.build, writer, 'naboj/x/pic', 'svg') == 'build/naboj/x/pic.svg'
        assert 'build/naboj/x/pic.svg: copy render/naboj/x/pic.svg' in written(writer)

    def test_a_plot_is_drawn_again_rather_than_converted(self, writer):
        """One step shorter, and it takes the PDF parser out of the chain for these files."""
        _picture_svg(writer.build, writer, 'naboj/x/plot', 'gp')
        assert 'build/naboj/x/plot.svg: gnuplot_svg build/naboj/x/plot.gp' in written(writer)

    @pytest.mark.parametrize('extension', ['tikz', 'pdf'])
    def test_everything_else_is_converted_from_the_printed_pdf(self, writer, extension):
        _picture_svg(writer.build, writer, 'naboj/x/pic', extension)
        assert 'build/naboj/x/pic.svg: pdf_svg build/naboj/x/pic.pdf' in written(writer)

    def test_a_picture_reached_twice_is_declared_once(self, writer):
        """
        `seminar/FKS/35/1/2/02` holds both `svah.svg` and `svah.pdf`. The PDF side resolves that
        by rule order and this side must not then declare a second edge for the same output --
        Ninja refuses the graph outright, which is how the PDF case was found.
        """
        _picture_svg(writer.build, writer, 'seminar/x/svah', 'svg')
        assert _picture_svg(writer.build, writer, 'seminar/x/svah', 'pdf') \
            == 'build/seminar/x/svah.svg'
        assert written(writer).count('build/seminar/x/svah.svg:') == 1


class TestWhereAPageLooksForItsFragments:
    """
    Náboj holds a directory per language inside a problem; seminar is monolingual and its
    fragments sit in the unit directory. `page.py` reads that out of the module's descriptor,
    so the edge has to agree with it or the page is assembled from the wrong directory.
    """

    def test_naboj_nests_the_language(self, writer):
        page = _page(writer.build, 'naboj/phys/29/problems/drenched', 'sk', 'naboj',
                     fragments=['build/naboj/phys/29/problems/drenched/sk/solution.html'],
                     pictures=[], nested=True)
        assert page == 'output/naboj/phys/29/problems/drenched/sk/index.html'
        assert 'unit = build/naboj/phys/29/problems/drenched' in written(writer)
        assert 'module = naboj' in written(writer)

    def test_seminar_does_not(self, writer):
        page = _page(writer.build, 'seminar/FKS/42/1/1/01', 'sk', 'seminar',
                     fragments=['build/seminar/FKS/42/1/1/01/problem.html'],
                     pictures=[], nested=False)
        assert page == 'output/seminar/FKS/42/1/1/01/index.html'

    def test_it_waits_for_the_maths_the_booklet_is_set_with(self, writer):
        r"""
        `mathpage.jtex` `\input`s the language's i18n table and five of `core/latex/`. The
        document edges learn those from xelatex's `-recorder`; a page runs its xelatex inside
        `core.html.texmath`, where there is no recorder, so the edge has to name them.
        """
        _page(writer.build, 'naboj/x', 'sk', 'naboj', fragments=['build/naboj/x/sk/a.html'],
              pictures=[], nested=True)
        line = written(writer).splitlines()[0]
        for wanted in ('build/core/i18n/sk.tex', 'core/templates/mathpage.jtex',
                       'core/latex/math.tex', 'core/templates/page.jhtml',
                       'core/html/page.css'):
            assert wanted in line, wanted


class TestWhichPicturesAPageNames:
    def test_only_the_ones_in_the_units_own_directory(self):
        """
        An exact directory match, not a prefix. Scholar's issue directory *contains* its
        problems, so a prefix would hand an issue's page every drawing below it.
        """
        drawings = ['build/scholar/TA1/2018/handouts/02/cylinder.svg',
                    'build/scholar/TA1/2018/handouts/02/01/graph.svg']
        assert _beside(drawings, 'scholar/TA1/2018/handouts/02') == [drawings[0]]
        assert _beside(drawings, 'scholar/TA1/2018/handouts/02/01') == [drawings[1]]


class TestTheEditorsPreview:
    """
    `modules/<module>/editor.yaml` names `output/<unit>/standalone.pdf` as its `preview:`, and
    `/api/compile` asks for that and nothing else -- so a module whose standalone has no edge
    has an editor that renders and converts and then cannot show the page. Seminar and scholar
    were in exactly that state while make built both.
    """

    def test_it_builds_the_target_the_descriptor_names(self, writer):
        assert _standalone(writer.build, 'seminar', 'seminar/FKS/42/1/3/01',
                           [], [], 'sk') == 'output/seminar/FKS/42/1/3/01/standalone.pdf'

    def test_the_builder_is_given_the_path_below_its_own_source_root(self, writer):
        """
        `-l/--launch` defaults to `source/<module>/`, so the argument is the unit *below* that.
        Passing the whole `seminar/FKS/...` would look right and resolve one level too high.
        """
        _standalone(writer.build, 'seminar', 'seminar/FKS/42/1/3/01', [], [], 'sk')
        assert '\n  unit = FKS/42/1/3/01\n' in written(writer)

    def test_a_scholar_sheet_and_a_problem_below_it_each_get_one(self, writer):
        """Both shapes `editor.yaml` declares: the issue holding `text.md`, and a problem."""
        for rel in ('scholar/TA1/2025/handouts/01', 'scholar/TA1/2025/handouts/01/1-wien'):
            assert _standalone(writer.build, 'scholar', rel, [], [], 'sk') \
                == f'output/{rel}/standalone.pdf'

    def test_the_pdf_waits_for_the_tex_and_the_class(self, writer):
        _standalone(writer.build, 'seminar', 'seminar/FKS/42/1/3/01',
                    ['build/seminar/FKS/42/1/3/01/problem.tex'], [], 'sk')
        pdf = next(line for line in written(writer).splitlines()
                   if 'document_pdf' in line)
        for wanted in ('build/seminar/FKS/42/1/3/01/standalone.tex',
                       'build/seminar/FKS/42/1/3/01/problem.tex',
                       'build/core/i18n/sk.tex', 'core/latex/dgs.cls'):
            assert wanted in pdf, wanted


class TestTheInstagramPages:
    """
    One page per problem is a fact about `instagram.jtex`, not a thing to discover by listing
    whatever `pdftoppm` happened to write -- so the pages are declared, and a document that
    does not have that many stops the build instead of being cut into misnumbered images.
    """

    PREFIX = 'output/seminar/FKS/42/1/3/instagram'
    COUNTED = 'build/seminar/FKS/42/1/3/instagram.pages'

    def test_there_is_one_image_per_problem(self, writer):
        assert _instagram(writer.build, self.PREFIX, self.COUNTED, 3) == [
            f'{self.PREFIX}-01.png', f'{self.PREFIX}-02.png', f'{self.PREFIX}-03.png']

    def test_every_page_waits_for_the_count_to_be_checked(self, writer):
        _instagram(writer.build, self.PREFIX, self.COUNTED, 3)
        pages = [line for line in written(writer).splitlines() if 'page_image' in line]
        assert len(pages) == 3
        for page in pages:
            assert f'{self.PREFIX}.pdf | {self.COUNTED}' in page, page

    def test_the_check_is_told_how_many_pages_to_expect(self, writer):
        _instagram(writer.build, self.PREFIX, self.COUNTED, 7)
        written_out = written(writer)
        assert f'build {self.COUNTED}: page_count {self.PREFIX}.pdf' in written_out
        assert '\n  pages = 7\n' in written_out

    def test_a_page_names_itself_as_pdftoppms_prefix(self, writer):
        """`-singlefile` writes `<prefix>.png`, so the prefix is the output without its suffix."""
        _instagram(writer.build, self.PREFIX, self.COUNTED, 1)
        assert f'\n  prefix = {self.PREFIX}-01\n' in written(writer)
