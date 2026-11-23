"""
The seam between a builder and the build graph.

`core/builder/products.py` states it: *a builder declares the set of files one invocation writes;
the graph declares everything else.* These pin that the two sides read the one declaration, that
the rule for an optional product is written once rather than three times, and that a template
cannot quietly assume an optional product is there.

Every check gets two tests, per the house rule: one that it fires on the thing it is for, and one
that it stays quiet on a case that looks like that thing and is not. The quiet halves here are the
real content -- a missing *module* template must still raise rather than vanish, and a bare
`\\input` of a product that is always written is correct and must not be reported.
"""
import pathlib
import re

import pytest

from core.builder import declaration as core_declaration
from core.builder.products import Node, Product, Root, read_scalar, written

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Every declaration that ships. Imported by name rather than discovered, because a module whose
#: declaration stopped being imported anywhere would otherwise drop out of these checks silently.
MODULES = ('naboj', 'seminar', 'scholar')


def declarations():
    """`(module, node)` for every node in every module, plus core's own."""
    import importlib
    out = [('core', core_declaration.I18N)]
    for module in MODULES:
        spec = importlib.import_module(f'modules.{module}.declaration')
        out += [(module, node) for node in spec.NODES.values()]
    return out


class TestWhichProductsAreWritten:
    """`written()` is the one statement of *this output exists only when its source does*."""

    NODE = Node('venue', (
        Product('instructions', 'instructions.jtex'),
        Product('inner', 'instructions-inner.jtex', root=Root.LANGUAGE, optional=True),
    ))

    def roots(self, tmp_path, *, inner: bool):
        templates, language = tmp_path / 'templates', tmp_path / 'language'
        templates.mkdir()
        language.mkdir()
        (templates / 'instructions.jtex').write_text('x')
        if inner:
            (language / 'instructions-inner.jtex').write_text('y')
        return {Root.TEMPLATES: templates, Root.LANGUAGE: language}

    def test_an_optional_product_with_no_source_is_not_written(self, tmp_path):
        names = [p.name for p in written(self.NODE, self.roots(tmp_path, inner=False))]
        assert names == ['instructions']

    def test_an_optional_product_with_a_source_is_written(self, tmp_path):
        names = [p.name for p in written(self.NODE, self.roots(tmp_path, inner=True))]
        assert names == ['instructions', 'inner']

    def test_a_required_product_is_written_even_with_no_template(self, tmp_path):
        """
        The quiet case, and the important one.

        A *module* template that is missing is a bug, and the build must stop on it with
        `TemplateNotFound` naming the file. If `written()` filtered on existence regardless of
        `optional`, a mistyped template name would instead produce a document that simply never
        appears -- the silent failure this whole arrangement exists to end.
        """
        roots = self.roots(tmp_path, inner=False)
        (roots[Root.TEMPLATES] / 'instructions.jtex').unlink()
        assert [p.name for p in written(self.NODE, roots)] == ['instructions']

    def test_a_root_nobody_supplied_drops_only_its_optional_products(self, tmp_path):
        """A venue whose meta names no language has no `LANGUAGE` root to look in."""
        roots = {Root.TEMPLATES: self.roots(tmp_path, inner=True)[Root.TEMPLATES]}
        assert [p.name for p in written(self.NODE, roots)] == ['instructions']

    def test_order_is_the_declarations(self, tmp_path):
        """
        Load-bearing rather than tidy: the three loops this replaced rendered the module's
        templates first and the node's own second, and a template that read a file a sibling had
        just written would see the difference.
        """
        roots = self.roots(tmp_path, inner=True)
        assert [p.name for p in written(self.NODE, roots)] == list(self.NODE.names())


class TestEveryShippedDeclaration:
    @pytest.mark.parametrize('module,node', declarations(), ids=lambda x: getattr(x, 'target', x))
    def test_no_module_template_is_optional(self, module, node):
        """
        `optional` means *the author of this content may not have written it*. A template that
        ships with the module is always there, and marking one optional would turn a typo into a
        document that silently never appears.
        """
        for product in node.products:
            if product.root is Root.TEMPLATES:
                assert not product.optional, f'{module}:{node.target}:{product.name}'

    @pytest.mark.parametrize('module,node', declarations(), ids=lambda x: getattr(x, 'target', x))
    def test_product_filenames_are_unique(self, module, node):
        """
        Filenames, not names: `core`'s two products are both called `{ident}` and are told apart
        by their suffix, which is the whole of why `Product` states one instead of deriving it
        from the template.
        """
        names = [product.filename('x') for product in node.products]
        assert len(set(names)) == len(names), f'{module}:{node.target}'

    @pytest.mark.parametrize('module,node', declarations(), ids=lambda x: getattr(x, 'target', x))
    def test_every_required_template_is_on_disk(self, module, node):
        """A required product names a template that ships; nothing else can be required."""
        root = ROOT / ('core/templates' if module == 'core' else f'modules/{module}/templates')
        for product in node.products:
            if product.root is Root.TEMPLATES:
                assert (root / product.template).is_file(), \
                    f'{module}:{node.target}:{product.template}'


class TestTheGraphAgreesWithTheBuilders:
    """
    The PDF lists stay in `tools/ninja/generate.py` because no builder has them -- `build/`
    cannot tell you which `.tex` XeLaTeX is pointed at -- but they must name products that are
    actually written.
    """

    def test_every_pdf_is_a_product(self):
        from modules.naboj import declaration as naboj
        from modules.seminar import declaration as seminar
        from tools.ninja import generate
        for pdfs, node in ((generate.LANGUAGE_PDFS, naboj.LANGUAGE),
                           (generate.VENUE_PDFS, naboj.VENUE),
                           (generate.ROUND_PDFS, seminar.ROUND)):
            assert set(pdfs) <= set(node.names()), \
                f'{node.target}: {set(pdfs) - set(node.names())} is printed but never written'

    def test_a_product_need_not_be_a_pdf(self):
        """
        The quiet half. `intro`, `evaluators` and `instructions-inner` are fragments another
        document `\\input`s, not documents anybody prints, so their absence from the PDF lists is
        correct and must not be read as a gap.
        """
        from modules.naboj import declaration as naboj
        from tools.ninja import generate
        assert set(naboj.LANGUAGE.names()) - set(generate.LANGUAGE_PDFS) == {'intro', 'evaluators'}
        assert set(naboj.VENUE.names()) - set(generate.VENUE_PDFS) == {'instructions-inner'}


class TestATemplateMayNotAssumeAnOptionalProduct:
    """
    The third layer, and the one that cost two bugs.

    An optional product may legitimately be absent, so a template that `\\input`s one must use
    `\\protectedInput` -- which prints a red `Missing file` box and carries on -- or guard the
    include behind a condition. A bare `\\input` is an `Emergency stop` with nothing naming the
    file: `instructions.jtex` did it for `instructions-inner.tex` and `evaluation.jtex` for
    `evaluators.tex`, the second surviving because its sibling `answers-modulo.jtex` reached the
    same file correctly and nobody compared them.
    """

    def naboj_templates(self):
        return sorted((ROOT / 'modules/naboj/templates').rglob('*.jtex'))

    def optional_products(self):
        from modules.naboj import declaration as naboj
        return {p.name for node in naboj.NODES.values() for p in node.products if p.optional}

    def guarded(self, text: str, position: int) -> bool:
        """Whether the include at `position` sits inside a Jinja `(@ if ... @)`."""
        before = text[:position]
        return before.count('(@ if ') > before.count('(@ endif @)')

    def test_no_unguarded_input_of_an_optional_product(self):
        offenders = []
        for template in self.naboj_templates():
            text = template.read_text()
            for name in self.optional_products():
                for match in re.finditer(r'\\(protectedInput|input)\{[^}]*?/' + re.escape(name)
                                         + r'\.tex\}', text):
                    if match.group(1) == 'input' and not self.guarded(text, match.start()):
                        offenders.append(f'{template.relative_to(ROOT)}: {name}')
        assert not offenders, 'unguarded \\input of an optional product: ' + '; '.join(offenders)

    def test_a_required_product_may_be_input_bare(self):
        """
        The quiet case. `base-booklet.jtex` `\\input`s core's i18n table, which is always
        written, and that is correct -- the rule is about optionality, not about `\\input`.
        """
        base = (ROOT / 'modules/naboj/templates/base-booklet.jtex').read_text()
        assert re.search(r'\\input\{build/core/i18n/', base)
        assert not any(p.optional for p in core_declaration.I18N.products)


class TestTheVenuesLanguage:
    """
    The graph cannot build a context, so it reads the venue's language off the meta itself. The
    guess is pinned against the authority rather than trusted.
    """

    def test_a_meta_with_no_language_reads_as_none(self, tmp_path):
        meta = tmp_path / 'meta.yaml'
        meta.write_text('id: 121\ncode: SKBAJ\n')
        assert read_scalar(meta, 'language') is None

    def test_a_comment_and_quotes_are_stripped(self, tmp_path):
        meta = tmp_path / 'meta.yaml'
        meta.write_text("language: 'cs'   # the venue is in Olomouc\n")
        assert read_scalar(meta, 'language') == 'cs'

    def test_the_word_inside_another_value_is_not_a_key(self, tmp_path):
        """The quiet case: `language` appearing in somebody else's value is not the key."""
        meta = tmp_path / 'meta.yaml'
        meta.write_text('name: School of language studies\nlanguage: hu\n')
        assert read_scalar(meta, 'language') == 'hu'

    def test_an_empty_value_reads_as_absent(self, tmp_path):
        meta = tmp_path / 'meta.yaml'
        meta.write_text('language:\n')
        assert read_scalar(meta, 'language') is None


@pytest.mark.skipif(not (pathlib.Path('source') / 'naboj').is_dir(),
                    reason='needs the naboj content repositories')
class TestTheGuessMatchesTheAuthority:
    """
    The sweep that makes the line scan trustworthy: over every venue meta in the checkout, what
    the graph reads must equal what the context computes. This test imports the context
    machinery; the graph deliberately does not.
    """

    def test_every_venue_meta_agrees(self):
        import yaml
        from modules.naboj import declaration
        for meta in sorted(pathlib.Path('source/naboj').glob('*/*/venues/*/meta.yaml')):
            try:
                parsed = yaml.safe_load(meta.read_text()) or {}
            except yaml.YAMLError:
                continue
            assert declaration.venue_language(meta) == (parsed or {}).get('language'), meta

    def test_a_booklet_that_wants_an_intro_has_one(self):
        """
        The guard and the product are *different* conditions, and nothing makes them agree.

        `booklet.jtex` includes `intro.tex` behind `language.booklet.contents.intro`, while the
        file is written only where that language holds an `intro.jtex`. A language declaring the
        first without the second is a bare `\\input` of a file nobody wrote -- the same
        `Emergency stop` as `instructions-inner` and `evaluators`, waiting. They agree across the
        whole corpus today and this is what says so.
        """
        import yaml
        wrong = []
        for meta in sorted(pathlib.Path('source/naboj').glob('*/*/languages/*/meta.yaml')):
            if 'fks-naboj' in meta.parts:
                continue
            try:
                parsed = yaml.safe_load(meta.read_text()) or {}
            except yaml.YAMLError:
                continue
            wants = ((parsed.get('booklet') or {}).get('contents') or {}).get('intro')
            if wants and not (meta.parent / 'intro.jtex').is_file():
                wrong.append(str(meta.parent))
        assert not wrong, 'booklet wants an intro that is not written: ' + '; '.join(wrong)


class TestTheValidatorAgreesWithTheDeclaration:
    """
    `NabojValidator` says what a volume's tree may contain; the declaration says what the
    builders write and what a problem holds. They are the same facts, and the validator used to
    restate them -- wrongly, in four places, each agreeing with the corpus by accident:

    - `intro.jtex` was **required** where `declaration.LANGUAGE` marks it optional, so the first
      language written without one would fail validation from a builder whose own declaration
      says it need not exist;
    - `answer.md` was **required** where the graph emits its edge only `if … .is_file()`;
    - the asset pattern had no `pdf`, which `PICTURE_COPIES` has, so a problem shipping a
      ready-made PDF drawing would build and fail to validate;
    - `venues/<v>/instructions-inner.tex` was still admitted after that file moved into the
      language directory, matching nothing at all.

    Deriving removes all four. These assert the derivation rather than the result, so the next
    product added to a node arrives in the schema without anybody editing it.
    """

    def schema(self):
        from modules.naboj.builder.contexts.validators import NabojValidator
        return NabojValidator._schema.schema

    def keys_of(self, mapping):
        """Every key of a schema mapping as a plain string, `Optional` unwrapped."""
        return {getattr(key, 'schema', key) for key in mapping}

    def test_a_problems_translated_files_are_the_declarations(self):
        from modules.naboj import declaration
        problems = self.schema()['problems'][str]
        language = next(value for key, value in problems.items() if callable(key))
        named = {name for name in self.keys_of(language) if str(name).endswith('.md')}
        assert named == {f'{name}.md' for name in declaration.TRANSLATED}

    def test_a_problems_shared_files_are_the_declarations(self):
        from modules.naboj import declaration
        named = {name for name in self.keys_of(self.schema()['problems'][str])
                 if str(name).endswith('.md')}
        assert named == {f'{name}.md' for name in declaration.SHARED}

    def test_nothing_a_problem_holds_is_required(self):
        """
        Every `.md` is `Optional`, and `answer.md` is the one that was not. A problem whose
        answer is a drawing, or which has not been given one yet, builds -- `generate.py` emits
        that edge conditionally -- and used to fail validation.
        """
        from enschema import Optional
        problems = self.schema()['problems'][str]
        required = [key for key in problems
                    if isinstance(key, str) and str(key).endswith('.md')]
        assert not required, f'{required} are required of every problem, and need not exist'
        assert any(isinstance(key, Optional) for key in problems)

    def test_a_language_directory_takes_every_product_rooted_in_one(self):
        from core.builder.products import Root
        from modules.naboj import declaration
        language = next(value for key, value in self.schema()['languages'].items()
                        if callable(key))
        wanted = {product.template
                  for node in declaration.NODES.values() for product in node.products
                  if product.root in (Root.UNIT, Root.LANGUAGE)}
        assert wanted <= self.keys_of(language)
        assert 'instructions-inner.jtex' in wanted, \
            "the venue's language-rooted product lives in a language directory too"

    def test_an_optional_product_is_optional_in_the_schema_too(self):
        """The firing case for the contradiction that cost the most: `intro.jtex`."""
        from enschema import Optional
        language = next(value for key, value in self.schema()['languages'].items()
                        if callable(key))
        for key in language:
            if getattr(key, 'schema', key) == 'intro.jtex':
                assert isinstance(key, Optional), 'intro.jtex is optional in the declaration'
                break
        else:
            raise AssertionError('intro.jtex is not in the schema at all')

    def test_the_language_meta_is_still_required(self):
        """
        The quiet case. Deriving the *products* must not make everything optional: a language
        directory with no `meta.yaml` is not a language, and that is not a product of anything.
        """
        language = next(value for key, value in self.schema()['languages'].items()
                        if callable(key))
        assert 'meta.yaml' in [key for key in language if isinstance(key, str)]

    def test_a_venue_holds_its_meta_and_nothing_else(self):
        venues = self.schema()[next(key for key in self.schema()
                                    if getattr(key, 'schema', key) == 'venues')]
        venue = next(iter(venues.values()))
        assert self.keys_of(venue) == {'meta.yaml'}


class TestTheAssetExtensionsAreOneList:
    def test_every_picture_the_graph_builds_may_sit_beside_a_problem(self):
        """
        The validator's pattern and the graph's two picture tables were separate lists, and the
        validator's was missing `pdf`. Nothing in the repository ships one, which is why nobody
        had met it.
        """
        from modules.naboj import declaration
        from tools.ninja import generate
        buildable = set(generate.PICTURE_SOURCES) | set(generate.PICTURE_COPIES)
        assert buildable <= set(declaration.ASSET_EXTENSIONS)

    def test_the_extras_are_what_a_plot_reads(self):
        """
        The quiet half: the list is deliberately *wider* than what the graph draws. `py` and
        `dat` are a listing and a plot's data, `tex` is a hand-written fragment -- none is a
        picture, and all three legitimately sit beside a problem.
        """
        from modules.naboj import declaration
        from tools.ninja import generate
        buildable = set(generate.PICTURE_SOURCES) | set(generate.PICTURE_COPIES)
        assert set(declaration.ASSET_EXTENSIONS) - buildable == {'py', 'dat', 'tex'}


class TestTheAuditsListsAreSubsetsOfTheBuilds:
    """
    Two lists in `core/audit/` name build targets and translated files, and neither was pinned
    to the thing it names. A subset is the right shape for both -- the audit deliberately checks
    fewer things than the build makes -- but an *unchecked* subset fails silently in the wrong
    direction: the day a name leaves the build, the audit goes on asking for it.
    """

    def test_every_target_the_build_check_compiles_is_one_the_graph_emits(self):
        from core.audit.build import TARGETS
        from tools.ninja import generate
        assert set(TARGETS['naboj']) <= set(generate.LANGUAGE_PDFS), \
            f"{set(TARGETS['naboj']) - set(generate.LANGUAGE_PDFS)} is compiled but never built"

    def test_it_is_deliberately_fewer(self):
        """
        The quiet half. These checks shell out to xelatex, so the list is the documents worth
        minutes rather than every document there is; `cover`, `constants`, `evaluation` and
        `online` are left out on purpose and their absence is not a gap.
        """
        from core.audit.build import TARGETS
        from tools.ninja import generate
        assert set(generate.LANGUAGE_PDFS) - set(TARGETS['naboj']) == {
            'cover', 'constants', 'evaluation', 'online'}

    def test_the_files_a_translation_is_judged_on_are_files_the_module_has(self):
        from core.audit import status
        from modules.naboj import declaration
        assert set(status.TRANSLATED) <= {f'{name}.md' for name in declaration.TRANSLATED}

    def test_a_translation_is_judged_on_fewer_files_than_it_may_hold(self):
        """
        Also deliberate, and the reason it is a subset rather than the list: `problem-extra.md`
        and `answer-extra.md` are extra content only some problems carry, so a language without
        one has a gap to show, not a missing translation.
        """
        from core.audit import status
        from modules.naboj import declaration
        assert {f'{name}.md' for name in declaration.TRANSLATED} - set(status.TRANSLATED) == {
            'problem-extra.md', 'answer-extra.md'}


class TestTheTwoLanguageSweepsAgree:
    def test_neither_counts_a_dot_directory_as_a_language(self, tmp_path):
        """
        `core/audit/build.py` and `tools/ninja/generate.py` each answer "which languages does
        this volume have", and only the graph's used to skip a hidden directory. The audit's
        answer feeds `run_targets`, which would then ask Ninja for a target it refuses by name
        and fail the whole row.
        """
        from core.audit.build import languages_of as audits
        from tools.ninja.generate import languages_of as graphs

        volume = tmp_path / 'phys' / '29'
        for name in ('sk', 'en', '.template'):
            (volume / 'languages' / name).mkdir(parents=True)

        assert audits(tmp_path, 'phys/29') == ['en', 'sk']
        assert graphs(volume) == ['en', 'sk']

    def test_a_volume_with_no_languages_directory_yields_nothing(self, tmp_path):
        """The quiet case: seminar and scholar scopes have none, and that is not a defect."""
        from core.audit.build import languages_of as audits
        from tools.ninja.generate import languages_of as graphs

        (tmp_path / 'FKS' / '42').mkdir(parents=True)
        assert audits(tmp_path, 'FKS/42') == []
        assert graphs(tmp_path / 'FKS' / '42') == []


class TestAPoolIsNotAVolume:
    """
    `phys/pool` and `chem/pool` hold problems nobody has set yet -- picked from and moved into
    a volume when they are. Everything that reads a *problem* applies to them and should; they
    are the problems somebody is writing. Everything that assumes a volume around the problems
    does not: no running order, no language set, no venues, no booklet.

    `phys/pool` was the one scope of thirty-four that would not validate, and the error led with
    the missing `languages/` -- which was the least of it. Two real causes hid behind that: a
    problem sharing a drawing by **symlink**, which the schema refused although CLAUDE.md names
    symlinking as the way to share one; and a problem that is a `rover.py` and nothing else.
    """

    def validator(self):
        from modules.naboj.builder.contexts.validators import NabojValidator
        return NabojValidator

    def test_a_pool_takes_the_pool_schema(self, tmp_path):
        from modules.naboj.builder.contexts.validators import POOL, VOLUME
        (tmp_path / 'pool').mkdir()
        (tmp_path / '29').mkdir()
        assert self.validator()(tmp_path / 'pool').schema is POOL
        assert self.validator()(tmp_path / '29').schema is VOLUME

    def test_a_pool_problem_need_not_be_translated_at_all(self, tmp_path):
        """`phys/pool/stuck-rover` is one Python file. A reservoir holds drafts."""
        from modules.naboj.builder.contexts.validators import POOL
        stub = tmp_path / 'pool' / 'problems' / 'stuck-rover'
        stub.mkdir(parents=True)
        (stub / 'rover.py').write_text('print(1)\n')
        POOL.validate(self.validator()(tmp_path / 'pool').tree)

    def test_a_volumes_problem_must_be(self, tmp_path):
        """
        The quiet case, and why this is two schemas rather than one lenient one: a problem with
        no language directory is in no booklet, so in a volume it is a defect and stays one.
        """
        from enschema import SchemaError

        from modules.naboj.builder.contexts.validators import VOLUME
        volume = tmp_path / '29'
        (volume / 'problems' / 'stuck-rover').mkdir(parents=True)
        (volume / 'problems' / 'stuck-rover' / 'rover.py').write_text('print(1)\n')
        (volume / 'languages' / 'sk').mkdir(parents=True)
        (volume / 'languages' / 'sk' / 'meta.yaml').write_text('id: sk\n')
        (volume / 'meta.yaml').write_text('problems: []\n')
        with pytest.raises(SchemaError):
            VOLUME.validate(self.validator()(volume).tree)

    def test_a_shared_drawing_may_be_a_symlink(self, tmp_path):
        """
        CLAUDE.md: "Sharing one drawing between two problems is a symlink, not an `include()`."
        The schema said `File`, which refuses one, and `phys/pool/troll-69-limits` does exactly
        that with its `object.svg`. Four drawings in the repository are links.
        """
        from modules.naboj.builder.contexts.validators import POOL
        problems = tmp_path / 'pool' / 'problems'
        (problems / 'original').mkdir(parents=True)
        (problems / 'original' / 'object.svg').write_text('<svg/>')
        (problems / 'borrower').mkdir()
        (problems / 'borrower' / 'object.svg').symlink_to(problems / 'original' / 'object.svg')
        POOL.validate(self.validator()(tmp_path / 'pool').tree)

    def test_every_scope_in_the_checkout_validates(self):
        """The sweep that says the two schemas between them cover what is actually there."""
        import contextlib
        import glob
        import io
        failed = []
        for found in sorted(glob.glob('source/naboj/*/*/problems')):
            scope = pathlib.Path(found).parent
            if 'fks-naboj' in str(scope):
                continue                       # not ours, and built by nothing
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.validator()(scope).validate()
            except Exception:
                failed.append(str(scope))
        assert not failed, f'these do not validate: {failed}'


@pytest.mark.skipif(not (pathlib.Path('source') / 'naboj').is_dir(),
                    reason='needs the naboj content repositories')
class TestWhatAPoolIsExemptFrom:
    def test_the_volume_consistency_check_is_quiet(self):
        """
        `translation-set` asks whether a problem has the same languages as its neighbours, which
        is a question about a booklet: everything in one is translated into the same set. A pool
        is the opposite by construction, and the check was 31 of its 182 findings.
        """
        import glob

        from core.audit import checks
        from core.audit.sources import read_scope
        root = pathlib.Path('source/naboj')
        units = sorted(pathlib.Path(p).relative_to(root).as_posix()
                       for p in glob.glob('source/naboj/phys/pool/problems/*')
                       if pathlib.Path(p).is_dir())
        assert not list(checks.translation_set(read_scope(root, 'naboj', 'phys/pool', units)))

    def test_the_problem_checks_still_run(self):
        """The quiet half, and the point: a pool is audited, just not as a competition."""
        import glob

        from core.audit import audit
        root = pathlib.Path('source/naboj')
        units = sorted(pathlib.Path(p).relative_to(root).as_posix()
                       for p in glob.glob('source/naboj/phys/pool/problems/*')
                       if pathlib.Path(p).is_dir())
        report = audit(root, 'naboj', 'phys/pool', units)
        assert len(report.findings) > 50, 'a pool should still be read problem by problem'
        assert {f.check for f in report.findings} - {'translation-set'}

    def test_both_pools_are_visible_and_shaped_alike(self):
        """
        A pool is a reservoir somebody writes into, so it has to be openable and auditable --
        which means not dotted, and holding the `problems/` level the unit glob expects.

        chem's was `.pool/<pid>`: dotted, so every sweep skipped it, *and* one level short, so
        even undotted nothing would have found it. Both halves had to move. This is what stops
        the next pool being created the old way and quietly disappearing.
        """
        from tools.editor.descriptors import discover_units, load_modules
        module = load_modules(pathlib.Path('.'))['naboj']
        units = discover_units(module)
        for competition in ('phys', 'chem'):
            pool = pathlib.Path('source/naboj') / competition / 'pool'
            if not pool.is_dir():
                continue
            assert (pool / 'problems').is_dir(), \
                f'{competition}/pool has no problems/ level, so no sweep will find its units'
            assert any(unit.startswith(f'{competition}/pool/') for unit in units), \
                f'{competition}/pool holds no unit the editor can open'

    def test_no_pool_is_hidden_behind_a_dot(self):
        """The quiet case stated as the rule: a dotted pool is invisible to everything."""
        hidden = sorted(str(p) for p in pathlib.Path('source/naboj').glob('*/.pool'))
        assert not hidden, f'these pools are dotted and so are audited by nothing: {hidden}'

    def test_a_pool_builds_nothing(self):
        """
        No `languages/`, so the scope sweep in `tools/ninja/generate.py` never names it and no
        booklet edge exists. That is what "picked and moved into a volume" means mechanically.
        """
        assert not (pathlib.Path('source/naboj/phys/pool') / 'languages').is_dir()
