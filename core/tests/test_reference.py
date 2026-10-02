"""
The reference table, held to the code it describes.

A hand-written reference drifts. That is not a risk, it is the normal fate of one: somebody adds a
filter and does not know the document exists, or renames an output and the example beside it goes
on claiming the old one. The whole point of `core/builder/reference.py` being a table rather than
prose is that the drift can be made to fail a test instead, and these are those tests.

Three of them, and each closes a different gap:

- **coverage**, in both directions, so a filter cannot be registered without an entry and an entry
  cannot name a filter that does not exist;
- **the examples are executed**, so the output printed in the document is the output the code
  produces today;
- **the document on disk matches the generator**, so `docs/filters.md` cannot be edited by hand
  into something the table does not say.
"""
import collections
import subprocess
import sys

import jinja2
import pytest

from core.builder import reference
from core.builder.jinja import MarkdownJinjaRenderer, StaticRenderer
from core.builder.reference import MARKDOWN, META, STATIC, Entry


@pytest.fixture(scope='module')
def builtin():
    """Jinja's own tables, which everything below is measured against."""
    return jinja2.Environment()


@pytest.fixture(scope='module')
def environments():
    """The two renderers an author's text actually passes through."""
    return {MARKDOWN: MarkdownJinjaRenderer(), STATIC: StaticRenderer('.')}


def registered(environment, builtin, attribute):
    """
    The names one environment adds to Jinja's own.

    `|e` has to be named explicitly: it *overwrites* a Jinja builtin rather than adding a name, so
    a plain set difference loses it -- and losing it is exactly the sort of hole this file exists
    to close.
    """
    ours = getattr(environment.env, attribute)
    theirs = getattr(builtin, attribute)
    return {name for name in ours
            if name not in theirs or ours[name] is not theirs[name]}


def documented(kind, env):
    """Every name the table accounts for, precision families expanded."""
    return {name for entry in reference.REFERENCE if entry.kind == kind and entry.env == env
            for name in entry.names}


class TestCoverage:
    """
    The table's names and the registered names, compared **both ways**.

    One direction alone would be half a test. Only-forwards lets a new filter ship undocumented;
    only-backwards lets the document describe a filter that was deleted. Both have happened to
    other reference files in other repositories, which is why neither half is optional.
    """

    @pytest.mark.parametrize(('env', 'kind', 'attribute'), [
        (MARKDOWN, 'filter', 'filters'),
        (MARKDOWN, 'global', 'globals'),
        (STATIC, 'filter', 'filters'),
        (STATIC, 'global', 'globals'),
    ])
    def test_table_matches_the_environment(self, environments, builtin, env, kind, attribute):
        assert documented(kind, env) == registered(environments[env], builtin, attribute)

    def test_the_two_environments_are_disjoint(self, environments, builtin):
        """
        `|disp` works only in a `.md` and `|upnth` only in a `.jtex`, and nothing says so but this.

        Asserted because the document makes the claim in its own opening table. If the two ever
        grow a shared filter, that paragraph becomes wrong and somebody should have to notice.
        """
        markdown = registered(environments[MARKDOWN], builtin, 'filters')
        static = registered(environments[STATIC], builtin, 'filters')
        assert markdown & static == set()

    def test_exactly_one_filter_shadows_a_jinja_builtin(self, environments, builtin):
        """
        `|e` overwrites Jinja's `escape`, which is harmless only because `autoescape=False`.

        Pinned so that a second one cannot be added without the decision being made on purpose:
        shadowing `|join` or `|round` would change what an existing source file means.
        """
        ours = environments[MARKDOWN].env.filters
        shadowed = {name for name in ours
                    if name in builtin.filters and ours[name] is not builtin.filters[name]}
        assert shadowed == {'e'}

    def test_precision_families_are_complete(self):
        """A root claiming a family must have all ten variants registered, not some of them."""
        registered_filters = set(MarkdownJinjaRenderer().env.filters)
        for entry in reference.REFERENCE:
            if not entry.precisions:
                continue
            missing = {name for name in entry.names if name not in registered_filters}
            assert not missing, f'{entry.name}: {sorted(missing)} claimed but not registered'

    def test_no_two_entries_claim_the_same_name_and_kind(self):
        """
        `unit` is a filter, an attribute *and* a `values:` key, and that is fine; two entries for
        the same pair is not, because `lookup` would silently return whichever came first.
        """
        seen = collections.Counter(
            (entry.kind, name) for entry in reference.REFERENCE for name in entry.names)
        assert [pair for pair, count in seen.items() if count > 1] == []

    def test_every_jinja_builtin_entry_is_one(self, builtin):
        """An entry filed under Jinja's own must actually be Jinja's own, and not ours."""
        ours = registered(MarkdownJinjaRenderer(), builtin, 'filters')
        for entry in reference.REFERENCE:
            if entry.kind != 'jinja-builtin':
                continue
            assert entry.name in builtin.filters, f'{entry.name} is not a Jinja filter'
            assert entry.name not in ours, f'{entry.name} is ours, so it is not a builtin'


class TestExamples:
    """
    Every example is rendered and compared with the output written beside it.

    This is the half that makes the document worth reading: an example that passes here is one an
    author can paste. It is also the half that catches a change in behaviour nobody meant -- the
    expected outputs below were produced by running the code, so a filter whose output moves takes
    this file red with it rather than quietly making 102 printed examples wrong.
    """

    @pytest.mark.parametrize('entry', [e for e in reference.REFERENCE if e.example],
                             ids=lambda e: f'{e.kind}:{e.name}')
    def test_example_renders_to_its_stated_output(self, entry):
        assert reference.render_example(entry) == entry.expect

    #: The only entries allowed to go without one, each because rendering it would need something
    #: outside the example context: a file beside the template, or a loaded locale. Named rather
    #: than counted, so that adding a fifth is a decision somebody makes on purpose instead of a
    #: threshold quietly sliding.
    WITHOUT = frozenset({('global', 'include'), ('global', 'path_exists'),
                         ('global', 'file_size'), ('namespace', 'i18n')})

    def test_every_other_entry_carries_one(self):
        """
        A `meta.yaml` key is not a template and cannot have one; everything that *is* a template
        must, because an entry with no example is the half of the documentation that is actually
        read.
        """
        renderable = [e for e in reference.REFERENCE if e.env != META and e.kind != 'operator']
        missing = {(e.kind, e.name) for e in renderable if not e.example}
        assert missing == self.WITHOUT


class TestDocument:
    """`docs/filters.md` is generated, and this is what makes that true rather than aspirational."""

    def test_the_file_on_disk_matches_the_generator(self):
        generated = reference.render_markdown()
        assert reference.DOCUMENT.is_file(), \
            f'{reference.DOCUMENT} is missing; run `python -m core.builder.reference`'
        assert reference.DOCUMENT.read_text() == generated, \
            f'{reference.DOCUMENT} is stale; run `python -m core.builder.reference`'

    def test_check_exits_zero_on_a_clean_tree(self):
        """The CI shape, run the way CI would run it."""
        done = subprocess.run([sys.executable, '-m', 'core.builder.reference', '--check'],
                              capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stdout + done.stderr

    def test_every_entry_reaches_the_document(self):
        """A section no entry names, or an entry the generator skips, would be invisible."""
        document = reference.render_markdown()
        for entry in reference.REFERENCE:
            assert f'### `{entry.display}`' in document, f'{entry.display} is not in the document'


class TestLookup:
    """What the editor's hover calls, with the two cases that are easy to get wrong."""

    def test_a_precision_variant_resolves_to_its_root(self):
        assert reference.lookup('f2', kind='filter').name == 'f'
        assert reference.lookup('af7', kind='filter').name == 'af'

    def test_an_alias_resolves_to_its_entry(self):
        assert reference.lookup('QuantityRange', kind='global').name == 'QR'
        assert reference.lookup('equals', kind='attribute').name == 'eq'

    def test_the_kind_decides_between_homonyms(self):
        """`unit` is three different things, and the hover has to get the right one."""
        assert reference.lookup('unit', kind='filter').summary.startswith('The unit alone')
        assert reference.lookup('unit', kind='attribute').summary.startswith('The pint unit')
        assert reference.lookup('unit', kind='values-key').summary.startswith('The unit.')

    def test_an_unknown_name_is_none_rather_than_an_error(self):
        """The hover asks about whatever is under the pointer, so a miss has to be ordinary."""
        assert reference.lookup('nosuchfilter') is None
        assert reference.lookup('disp', kind='global') is None

    def test_the_json_payload_is_keyed_the_way_the_front_end_reads_it(self):
        payload = reference.as_json()
        assert payload['entries']['filter:f2']['root'] == 'f'
        assert payload['entries']['attribute:eq']['display'] == '.eq'
        assert 'Maths' in payload['sections']


class TestEntry:
    """The invariants `Entry.__post_init__` keeps, since a broken one would break the generator."""

    def test_an_example_and_its_output_come_as_a_pair(self):
        with pytest.raises(AssertionError):
            Entry('x', 'filter', 'summary', example='(§ x §)')

    def test_an_unknown_kind_is_refused(self):
        with pytest.raises(AssertionError):
            Entry('x', 'nonsense', 'summary')
