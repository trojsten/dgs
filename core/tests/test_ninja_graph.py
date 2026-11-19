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
    generate,
    _fragment,
    _instagram,
    _page,
    _picture_svg,
    _standalone,
    scholar_edges,
    seminar_edges,
    write_graph,
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
        drawings = ['build/scholar/TA1/handouts/02/cylinder.svg',
                    'build/scholar/TA1/handouts/02/01/graph.svg']
        assert _beside(drawings, 'scholar/TA1/handouts/02') == [drawings[0]]
        assert _beside(drawings, 'scholar/TA1/handouts/02/01') == [drawings[1]]


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
        for rel in ('scholar/TA1/handouts/01', 'scholar/TA1/handouts/01/1-wien'):
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


class TestTheGraphIsReplacedAndNeverTruncated:
    """
    `write_graph` writes beside the graph and renames, so a run that does not finish leaves the
    previous graph alone. Written in place it truncated first and filled for two seconds, and
    both ways out of that are a build nobody can run: Ninja deletes an in-flight edge's outputs
    on Ctrl-C when their mtime has moved, so an interrupt deleted `build.ninja`, and a generator
    that raised left a prefix of one -- which `bootstrap.ensure_graph` will not repair, because
    it fixes absence and a partial graph is present.

    `generate` is patched out, so none of this needs a source tree.
    """

    @staticmethod
    def write(monkeypatch, output, body):
        def fake_generate(repo, scopes, out):
            return body(out)

        monkeypatch.setattr('tools.ninja.generate.generate', fake_generate)
        return write_graph(output, pathlib.Path('/repo'), ['phys/29'])

    def test_a_complete_graph_lands(self, monkeypatch, tmp_path):
        graph = tmp_path / 'build.ninja'
        counts = self.write(monkeypatch, graph,
                            lambda out: (out.write('rule r\n'), {'edges': 1})[1])
        assert graph.read_text() == 'rule r\n'
        assert counts == {'edges': 1}

    def test_a_failed_run_leaves_the_old_graph(self, monkeypatch, tmp_path):
        graph = tmp_path / 'build.ninja'
        graph.write_text('the previous graph\n')

        def half_then_fail(out):
            out.write('half a rule')
            raise RuntimeError('a meta the generator could not read')

        with pytest.raises(RuntimeError):
            self.write(monkeypatch, graph, half_then_fail)
        assert graph.read_text() == 'the previous graph\n'

    def test_an_interrupted_run_leaves_the_old_graph(self, monkeypatch, tmp_path):
        """Ctrl-C is a `BaseException`, which is why the cleanup catches one."""
        graph = tmp_path / 'build.ninja'
        graph.write_text('the previous graph\n')

        def interrupted(out):
            out.write('half a rule')
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            self.write(monkeypatch, graph, interrupted)
        assert graph.read_text() == 'the previous graph\n'

    def test_nothing_is_left_beside_it_either_way(self, monkeypatch, tmp_path):
        """A temporary left behind would accumulate one per failed run, and they are hidden."""
        graph = tmp_path / 'build.ninja'

        def fail(out):
            raise RuntimeError('no')

        with pytest.raises(RuntimeError):
            self.write(monkeypatch, graph, fail)
        self.write(monkeypatch, graph, lambda out: (out.write('rule r\n'), {})[1])
        assert sorted(path.name for path in tmp_path.iterdir()) == ['build.ninja']

    def test_the_graph_is_readable_rather_than_mkstemps_0600(self, monkeypatch, tmp_path):
        graph = tmp_path / 'build.ninja'
        self.write(monkeypatch, graph, lambda out: (out.write('rule r\n'), {})[1])
        assert graph.stat().st_mode & 0o777 == 0o644


class TestHowDeepAScholarIssueGoes:
    r"""
    A scholar problem may hold subproblems, and the graph has to go down to them.

    This is the one module where a fragment lives two levels below the unit the builder is
    invoked for. `add_subdirs` finds a subproblem by listing the directory, so
    `homework-students.jtex` writes `\protectedInput{…/a-sub/problem.tex}` whatever the graph
    knows -- and while the graph stopped at the problem, that file was never built and the
    document printed a red `Missing file …!` box in its place. `STA/2023/homework/01` had four
    of them, and 42 subproblem directories across 8 issues were in the same state.

    The bound is the other half: `ContextIssueSubSub` declares no `_subcontext_key` and the
    templates have no heading below `\subsubsection`, so a fourth level is not something any
    document can input and rendering it would build fragments for nobody.
    """

    @pytest.fixture
    def repo(self, tmp_path):
        issue = tmp_path / 'source/scholar/XX/homework/01'
        for rel in ('', '1-problem', '1-problem/a-sub', '1-problem/a-sub/deeper'):
            place = issue / rel
            place.mkdir(parents=True)
            (place / 'meta.yaml').write_text('title: x\n')
            (place / ('text.md' if rel == '' else 'problem.md')).write_text('text\n')
        return tmp_path

    def edges(self, repo, writer) -> str:
        scholar_edges(repo, 'XX', writer)
        return written(writer)

    def test_a_subproblem_fragment_is_built(self, repo, writer):
        assert ('build/scholar/XX/homework/01/1-problem/a-sub/problem.tex'
                in self.edges(repo, writer))

    def test_the_document_names_it_as_a_prerequisite(self, repo, writer):
        """Built and not named is the same page: ninja would not build it before the xelatex."""
        pdf = [line for line in self.edges(repo, writer).splitlines()
               if line.startswith('build output/scholar/XX/homework/01/homework-students.pdf')]
        assert len(pdf) == 1
        assert 'build/scholar/XX/homework/01/1-problem/a-sub/problem.tex' in pdf[0]

    def test_the_issue_and_the_problem_are_still_there(self, repo, writer):
        """The quiet half above: adding a level must not cost either of the two that worked."""
        out = self.edges(repo, writer)
        assert 'build/scholar/XX/homework/01/text.tex' in out
        assert 'build/scholar/XX/homework/01/1-problem/problem.tex' in out

    def test_it_stops_there_and_does_not_recurse_for_ever(self, repo, writer):
        """The quiet half below: nothing can input a fragment a level deeper than a subproblem."""
        assert 'deeper' not in self.edges(repo, writer)

    def test_a_subproblem_directory_is_watched(self, repo, writer):
        """
        A directory the generator read is one whose change has to regenerate the graph. Without
        this, creating the first subproblem of a problem would leave the graph as it was and the
        new statement would come out as the box this test exists for.
        """
        counts = scholar_edges(repo, 'XX', writer)
        assert 'source/scholar/XX/homework/01/1-problem' in counts['listed']


class TestWhichLanguageAScopeIsSetIn:
    r"""
    A seminar competition and a scholar course each declare their language, and the graph has to
    read it rather than assume Slovak.

    Both modules are monolingual, which is why this was the literal `'sk'` at every call site --
    but monolingual means *one* language, not Slovak. `source/scholar/STA/meta.yaml` says
    `language: en`, and `modules/scholar/builder/standalone.py` has always honoured it, so the
    document was set in English while the fragments inside it went through pandoc with
    `core/i18n/sk.yaml`: `spacing.lua` glued `a~strong` by Slovak's one-letter-word rule and
    `hyphens.lua` broke `low-luminosity` as `low-` / `-luminosity`, repeating a hyphen in a
    language that does not. The two halves only meet on the page, which is why nothing failed.

    The fallback stays `sk` and is the quiet half of each pair below: a scope that declares
    nothing must keep the graph it had, which is every seminar round in the repository.
    """

    @pytest.fixture
    def scholar(self, tmp_path):
        def make(meta: str):
            issue = tmp_path / 'source/scholar/XX/homework/01'
            issue.mkdir(parents=True)
            (issue / 'meta.yaml').write_text('title: x\n')
            (issue / 'text.md').write_text('text\n')
            (tmp_path / 'source/scholar/XX/meta.yaml').write_text(meta)
            return tmp_path
        return make

    @pytest.fixture
    def seminar(self, tmp_path):
        def make(meta: str):
            problem = tmp_path / 'source/seminar/YY/42/1/1/01'
            problem.mkdir(parents=True)
            (problem / 'meta.yaml').write_text('title: x\n')
            (problem / 'problem.md').write_text('text\n')
            (tmp_path / 'source/seminar/YY/meta.yaml').write_text(meta)
            return tmp_path
        return make

    def test_a_scholar_course_is_rendered_in_the_language_it_declares(self, scholar, writer):
        counts = scholar_edges(scholar('title: x\nlanguage: en\n'), 'XX', writer)
        assert 'lang = en' in written(writer)
        assert 'lang = sk' not in written(writer)
        assert counts['needs']['languages'] == {'en'}

    def test_its_document_asks_for_that_i18n_table(self, scholar, writer):
        """The `\\input` the template writes and the prerequisite the graph declares are one."""
        scholar_edges(scholar('title: x\nlanguage: en\n'), 'XX', writer)
        pdf = [line for line in written(writer).splitlines()
               if line.startswith('build output/scholar/XX/homework/01/homework-students.pdf')]
        assert len(pdf) == 1
        assert 'build/core/i18n/en.tex' in pdf[0]
        assert 'build/core/i18n/sk.tex' not in pdf[0]

    def test_the_course_meta_is_watched(self, scholar, writer):
        """Changing `language:` must regenerate the graph, as changing a venue's does."""
        counts = scholar_edges(scholar('title: x\nlanguage: en\n'), 'XX', writer)
        assert 'source/scholar/XX/meta.yaml' in counts['read']

    def test_a_scholar_course_that_declares_nothing_is_still_slovak(self, scholar, writer):
        counts = scholar_edges(scholar('title: x\n'), 'XX', writer)
        assert 'lang = sk' in written(writer)
        assert 'lang = en' not in written(writer)
        assert counts['needs']['languages'] == {'sk'}

    def test_a_seminar_competition_is_read_the_same_way(self, seminar, writer):
        counts = seminar_edges(seminar('id: YY\nlanguage: en\n'), 'YY/42/1/1', writer)
        assert 'lang = en' in written(writer)
        assert 'lang = sk' not in written(writer)
        assert counts['needs']['languages'] == {'en'}
        assert 'source/seminar/YY/meta.yaml' in counts['read']

    def test_a_seminar_competition_that_declares_nothing_is_still_slovak(self, seminar, writer):
        counts = seminar_edges(seminar('id: YY\n'), 'YY/42/1/1', writer)
        assert 'lang = sk' in written(writer)
        assert counts['needs']['languages'] == {'sk'}


class TestWhatMakesTheGraphRegenerate:
    """
    Everything the generator looked at is both an input of the regenerate edge and a `phony`.

    The input is what notices a change; the phony is what makes a *removal* recoverable. An
    input with no rule that has gone missing is a hard error -- `needed by 'build.ninja',
    missing and no known rule to make it` -- and it is unrecoverable, because the edge that
    would notice the removal is the one Ninja is refusing to run. It was written for the
    directories and the files were left out, which cost a hand-deleted `build.ninja` the moment
    scholar's year level went and `source/scholar/STA/2023/meta.yaml` with it.

    A phony does not mask the file: Ninja still takes an existing target's mtime, so editing
    the meta still regenerates. That is what the directory half has always relied on.
    """

    @pytest.fixture
    def repo(self, tmp_path):
        issue = tmp_path / 'source/scholar/XX/homework/01'
        issue.mkdir(parents=True)
        (issue / 'meta.yaml').write_text('title: x\n')
        (issue / 'text.md').write_text('text\n')
        (tmp_path / 'source/scholar/XX/meta.yaml').write_text('title: x\nlanguage: en\n')
        return tmp_path

    def graph(self, repo) -> str:
        out = io.StringIO()
        generate(repo, ['scholar:XX'], out)
        return out.getvalue()

    def regenerate_edge(self, repo) -> str:
        return next(line for line in self.graph(repo).splitlines()
                    if line.startswith('build build.ninja:'))

    def test_a_file_the_generator_read_is_an_input(self, repo):
        assert 'source/scholar/XX/meta.yaml' in self.regenerate_edge(repo)

    def test_and_it_has_a_phony_so_deleting_it_is_recoverable(self, repo):
        assert 'build source/scholar/XX/meta.yaml: phony' in self.graph(repo)

    def test_a_directory_it_listed_still_has_both(self, repo):
        """The half that already worked, which generalising the loop must not drop."""
        assert 'source/scholar/XX/homework/01' in self.regenerate_edge(repo)
        assert 'build source/scholar/XX/homework/01: phony' in self.graph(repo)
