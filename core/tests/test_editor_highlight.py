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
#: A span, with whatever `data-` attributes it carries -- `data-ref` for a name the reference
#: table holds, `data-eval` for a fragment the editor can evaluate. The attributes have to be in
#: the pattern rather than left out of it: without them the match falls through to the *next*
#: `<span class="…">` and the body of one token swallows the tokens between, which is a corrupt
#: reading that no assertion would look wrong. Hence `DATA` matching *any* of them by name, so
#: that adding a third one cannot reintroduce that silently.
SPAN = re.compile(r'<span class="([\w-]+)"((?: data-[\w-]+="[^"]*")*)>(.*?)</span>', re.DOTALL)
DATA = re.compile(r'data-([\w-]+)="([^"]*)"')


def attributes(blob):
    return {name: htmllib.unescape(value) for name, value in DATA.findall(blob)}


@pytest.fixture(scope='module')
def quickjs_context():
    """The shipped file, loaded once. Everything below is called out of this one context."""
    context = quickjs.Context()
    context.eval(HIGHLIGHT_JS.read_text())
    return context


@pytest.fixture(scope='module')
def highlight(quickjs_context):
    """`highlight(text, mode)` as the browser would call it."""
    return quickjs_context.eval('highlight')


@pytest.fixture(scope='module')
def tokens(highlight):
    """Every highlighted span as (class, text), with the HTML escaping undone."""
    def call(text, mode):
        return [(cls, htmllib.unescape(body))
                for cls, _, body in SPAN.findall(highlight(text, mode))]
    return call


@pytest.fixture(scope='module')
def found(quickjs_context):
    """
    `collectReferences(text, mode)` as `app.js` calls it, as a list of dicts.

    Through `JSON.stringify`, because quickjs hands an array back as an opaque object with no
    Python sequence protocol -- the string is the only shape that crosses the boundary intact.
    """
    import json
    collect = quickjs_context.eval(
        '(function (text, mode) { return JSON.stringify(collectReferences(text, mode)); })')
    return lambda text, mode: json.loads(collect(text, mode))


@pytest.fixture(scope='module')
def refs(highlight):
    """Every span that names something the reference holds, as (ref, text), in order."""
    def call(text, mode):
        return [(attributes(blob)['ref'], htmllib.unescape(body))
                for _, blob, body in SPAN.findall(highlight(text, mode))
                if 'ref' in attributes(blob)]
    return call


@pytest.fixture(scope='module')
def spans(highlight):
    """Every highlighted span as {text, cls, attrs}, which is what the hover reads off the DOM."""
    def call(text, mode):
        return [{'cls': cls, 'attrs': attributes(blob), 'text': htmllib.unescape(body)}
                for cls, blob, body in SPAN.findall(highlight(text, mode))]
    return call


@pytest.fixture(scope='module')
def evals(quickjs_context):
    """`evaluableSources(text, mode)`: the distinct fragments `app.js` sends to `/api/evaluate`."""
    import json
    sources = quickjs_context.eval(
        '(function (text, mode) { return JSON.stringify(evaluableSources(text, mode)); })')
    return lambda text, mode: json.loads(sources(text, mode))


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


class TestReferences:
    """
    The `data-ref` a span carries, which is what the editor's hover looks up.

    These matter more than the colouring does, because a wrong `data-ref` is worse than none: it
    shows an author the documentation for something other than what is under their pointer, and
    nothing about that looks wrong on the page.
    """

    def test_a_filter_is_named_without_its_pipe(self, refs):
        assert refs("(§ v|f2 §)", 'dgs-md') == [('filter:f2', 'f2')]

    def test_an_attribute_is_named_without_its_dot(self, refs):
        assert refs("(§ v.eq §)", 'dgs-md') == [('attribute:eq', 'eq')]

    def test_a_call_is_a_global(self, refs):
        assert refs("(§ sqrt(2) §)", 'dgs-md') == [('global:sqrt', 'sqrt')]

    def test_the_whole_chain_is_resolved_in_document_order(self, refs):
        """Document order, not rule order: it is what a reader expects and what emission gives."""
        assert refs("(§ ceil(PQ(2.1, 'm')).to('cm')|f0 §)", 'dgs-md') == [
            ('global:ceil', 'ceil'),
            ('global:PQ', 'PQ'),
            ('attribute:to', 'to'),
            ('filter:f0', 'f0'),
        ]

    def test_a_filter_that_takes_an_argument_is_a_filter_and_not_a_call(self, refs):
        """
        `|snap(0.5)` matches both the filter rule and the call rule, and the filter rule is
        first. Order in `INNER` is the only thing deciding this, so it is worth an assertion.
        """
        assert refs("(§ b|snap(0.5) §)", 'dgs-md') == [('filter:snap', 'snap')]

    def test_an_attribute_call_is_an_attribute_and_not_a_global(self, refs):
        """The same collision the other way round: `.to('cm')` is not a global named `to`."""
        assert refs("(§ d.to('cm') §)", 'dgs-md') == [('attribute:to', 'to')]

    @pytest.mark.parametrize(('source', 'expected'), [
        ("(§ eq.kin §)", [('meta-key:eq', 'eq')]),
        ("(§ words.air §)", [('meta-key:words', 'words')]),
        ("(§ blocks.setup §)", [('meta-key:blocks', 'blocks')]),
        ("(§ i18n.andw §)", [('namespace:i18n', 'i18n')]),
    ])
    def test_a_namespace_is_itself_and_what_follows_it_is_not_an_attribute(
            self, refs, source, expected):
        """
        `eq.kin` is an equation and `const.g` is a constant. Neither is an attribute *of*
        anything, so the name after the dot must stay unclaimed -- otherwise the hover offers
        `.kin` as though `PhysicsQuantity` had one.
        """
        assert refs(source, 'dgs-md') == expected

    def test_a_constant_keeps_its_own_attributes(self, refs):
        """The exclusion is one level deep: `const.g` is a quantity and `.approx` is its own."""
        assert refs("(§ const.g.approx §)", 'dgs-md') == [
            ('namespace:const', 'const'),
            ('attribute:approx', 'approx'),
        ]

    def test_the_range_operator_is_named(self, refs):
        """How every one of the 85 answer intervals is written; `QR` is never spelled out."""
        assert refs("(§ (result % result_approx)|f2 §)", 'dgs-md') == [
            ('operator:%', '%'),
            ('filter:f2', 'f2'),
        ]

    def test_a_per_cent_in_a_format_string_is_not_the_range_operator(self, refs):
        """The quiet half: `'%02d'` has no spaces round its `%`, and that is what excludes it."""
        assert refs("(§ '%s-%02d'|format('fig', 7) §)", 'dgs-md') == [('filter:format', 'format')]

    def test_nothing_outside_a_tag_is_claimed(self, refs):
        """
        The other quiet half, and the one that would be most annoying to get wrong: prose is full
        of full stops, pipes and brackets, and none of it is Jinja.
        """
        assert refs('Rýchlosť v. Pozri obr. 3 (a kol.) | ďalej', 'dgs-md') == []
        assert refs(r'$E_\text{kin} = \frac{1}{2} m v^2$', 'dgs-md') == []

    def test_a_gnuplot_script_resolves_inside_its_tags_only(self, refs):
        source = "set xlabel 'v'\nset yrange [0:(§ vmax.mag §)]\n# a comment. not an attribute\n"
        assert refs(source, 'dgs-gnuplot') == [('attribute:mag', 'mag')]


class TestReferencesInAMeta:
    """
    The meta pane, which is where the vocabulary the hover exists for is actually written: 158 of
    the 160 `PQ` in the repository are in a `derived:` entry and two are in a `(§ … §)` tag.
    """

    META = (
        'id: demo\n'
        'values:\n'
        '  h:\n'
        '    magnitude: 5\n'
        '    unit: \\metre\n'
        'derived:\n'
        '  result: "(h * const.g).to(\'cm\')"\n'
        'eq:\n'
        '  kin: E = m v^2\n'
    )

    def test_a_top_level_key_is_a_meta_key(self, refs):
        found = dict(refs(self.META, 'dgs-yaml'))
        assert found['meta-key:values'] == 'values'
        assert found['meta-key:derived'] == 'derived'
        assert found['meta-key:eq'] == 'eq'

    def test_a_key_inside_values_is_a_values_key(self, refs):
        found = dict(refs(self.META, 'dgs-yaml'))
        assert found['values-key:magnitude'] == 'magnitude'
        assert found['values-key:unit'] == 'unit'

    def test_a_quantity_s_own_name_is_not_a_values_key(self, refs):
        """
        The quiet half, and it caught a real bug: `values:` has two levels and only the deeper one
        is the table's. `h:` is the author's own name for a quantity, so there is nothing to look
        up -- and claiming it would offer whatever the table happened to hold under that word.
        """
        assert 'values-key:h' not in dict(refs(self.META, 'dgs-yaml'))

    def test_the_two_levels_are_found_however_the_meta_is_indented(self, refs):
        """The name level is whichever indent comes first, not a hard-coded two spaces."""
        source = 'values:\n    h:\n        magnitude: 5\n'
        found = dict(refs(source, 'dgs-yaml'))
        assert found == {'meta-key:values': 'values', 'values-key:magnitude': 'magnitude'}

    def test_a_derived_expression_resolves_like_a_tag(self, refs):
        found = [pair for pair in refs(self.META, 'dgs-yaml')
                 if pair[0].startswith(('attribute:', 'namespace:', 'global:'))]
        assert found == [('namespace:const', 'const'), ('attribute:to', 'to')]

    def test_an_eq_entry_is_left_alone(self, refs):
        """
        `eq:` holds LaTeX, not an expression. `E = m v^2` has no dot and no pipe, but the point
        is that the scan is confined to `derived:` and does not go looking.
        """
        assert not [pair for pair in refs(self.META, 'dgs-yaml') if pair[1] in {'E', 'm', 'v'}]

    def test_a_comment_in_a_meta_is_not_scanned(self, refs):
        source = 'derived:\n  # see 29/folding-bath, and note the .to() there\n  x: "1"\n'
        assert [r for r, _ in refs(source, 'dgs-yaml') if r.startswith('attribute:')] == []


class TestTheCaretPath:
    """
    `collectReferences` is also called directly, by the F1 lookup in `app.js`, which has no DOM to
    hit-test against and asks which reference spans the caret instead.

    Worth its own tests because the two paths have to agree: a name the pointer can find and the
    caret cannot, or the other way round, would be the sort of inconsistency nobody reports and
    everybody notices.
    """

    SOURCE = "(§ v.eq §) and (§ d|f2 §)"

    @pytest.mark.parametrize(('caret', 'expected'), [
        (0, None),                 # on the opening delimiter
        (5, 'attribute:eq'),       # the `e` of `eq`
        (7, 'attribute:eq'),       # just past its end, where a caret sits after typing it
        (12, None),                # in the prose between the two tags
        (21, 'filter:f2'),
    ])
    def test_the_caret_resolves_what_is_under_it(self, found, caret, expected):
        at = [f['ref'] for f in found(self.SOURCE, 'dgs-md')
              if f['start'] <= caret <= f['end']]
        assert (at[0] if at else None) == expected

    def test_the_offsets_are_into_the_original_text(self, found):
        """
        Into the whole text, not into the tag -- `collectReferences` measures a match inside the
        region and has to add the region's own start back on. Getting that wrong would put every
        tooltip after the first tag on the wrong word, which is to say in every real file.
        """
        text = 'xxxxxxxxxx(§ v.eq §)'
        got = found(text, 'dgs-md')
        assert len(got) == 1
        assert text[got[0]['start']:got[0]['end']] == 'eq'

    def test_a_meta_resolves_by_caret_too(self, found):
        """The F1 path serves the meta pane as well, which is where `PQ` is actually written."""
        text = 'derived:\n  r: "PQ(1, \'m\').to(\'cm\')"\n'
        # `r` is in there too and carries no `ref` -- a quantity's own name is not in the table,
        # it is a thing to evaluate, which `TestEvaluableFragments` covers.
        assert {f['ref'] for f in found(text, 'dgs-yaml') if f['ref']} == {
            'meta-key:derived', 'global:PQ', 'attribute:to'}


class TestEvaluableFragments:
    """
    What the hover offers to evaluate, which is the other half of what it shows: the reference
    table says what a filter *is*, and this says what this fragment comes out as in this problem.

    Two sources, one attribute. A `(§ … §)` tag is evaluated as written, and a meta entry's own
    name is evaluated through the tag that would reach it -- so hovering `snell` under `eq:`
    answers for `(§ eq.snell §)` without anyone having to type it.
    """

    META = '\n'.join([
        'eq:',
        "  snell: 'a = b'",
        'values:',
        '  v0:',
        '    magnitude: 3',
        '    unit: m',
        'derived:',
        '  r: "v0 * 2"',
        'blocks:',
        '  setup: |',
        '    set term pdf',
        'words:',
        '  air:',
        '    sk: vzduch',
        '',
    ])

    def test_a_tag_is_evaluated_as_written(self, evals):
        assert evals('Preto (§ eq.snell|inl §).', 'dgs-md') == ['(§ eq.snell|inl §)']

    def test_every_piece_of_a_tag_carries_the_whole_tag(self, spans):
        """
        The tag is carved into siblings around the names inside it, so the pointer lands on one
        piece of it and never on the whole. Each piece has to answer for the tag it came out of
        or hovering the filter would offer nothing while hovering the space beside it worked.
        """
        got = spans('(§ eq.snell|inl §)', 'dgs-md')
        assert [s['text'] for s in got] == ['(§ ', 'eq', '.snell|', 'inl', ' §)']
        assert {s['attrs'].get('eval') for s in got} == {'(§ eq.snell|inl §)'}

    def test_maths_is_not_evaluable(self, spans):
        """`$x$` is not a tag and there is nothing to evaluate in it; the popup must not claim so."""
        assert all('eval' not in s['attrs'] for s in spans('$x = y$', 'dgs-md'))

    @pytest.mark.parametrize(('name', 'expected'), [
        ('snell', '(§ eq.snell §)'),
        ('v0', '(§ v0 §)'),
        ('r', '(§ r §)'),
        ('setup', '(§ blocks.setup §)'),
        ('air', '(§ words.air §)'),
    ])
    def test_a_meta_entry_is_reached_the_way_a_template_reaches_it(self, spans, name, expected):
        by_text = {s['text']: s['attrs'].get('eval')
                   for s in spans(self.META, 'dgs-yaml')}
        assert by_text[name] == expected

    @pytest.mark.parametrize('key', ['magnitude', 'unit', 'sk'])
    def test_the_deeper_level_is_not_an_entry(self, spans, key):
        """
        `values:` and `words:` have two levels and only the shallower one names something a
        template may write. `(§ magnitude §)` is not a thing, and offering it would be an
        invitation to type it.
        """
        # By suffix, not by exact text: a key the reference rules did not carve out keeps the
        # indent the YAML rule matched with it, which is how `sk` under `words.air` arrives.
        at = [s for s in spans(self.META, 'dgs-yaml') if s['text'].strip() == key]
        assert at and all('eval' not in s['attrs'] for s in at)

    @pytest.mark.parametrize('key', ['eq', 'values', 'derived', 'blocks', 'words'])
    def test_the_block_name_itself_is_a_reference_and_not_an_entry(self, spans, key):
        by_text = {s['text']: s['attrs'] for s in spans(self.META, 'dgs-yaml')}
        assert by_text[key] == {'ref': f'meta-key:{key}'}

    def test_a_meta_indented_otherwise_still_works(self, evals):
        """
        The entry level is whichever indent comes first in that block, not a hard-coded two
        spaces -- and per block, since nothing says a file indents `eq:` and `values:` alike.
        """
        text = 'eq:\n    snell: \'a = b\'\nvalues:\n  v0:\n    magnitude: 3\n'
        assert evals(text, 'dgs-yaml') == ['(§ eq.snell §)', '(§ v0 §)']

    def test_a_tag_inside_a_meta_entry_is_evaluable_too(self, evals):
        """An `eq:` entry interpolating a value: both the entry and the tag inside it answer."""
        text = 'eq:\n  t: \'T = (§ t1|f0 §)\'\n'
        assert evals(text, 'dgs-yaml') == ['(§ t1|f0 §)', '(§ eq.t §)']

    def test_each_distinct_fragment_is_asked_for_once(self, evals):
        """The list is what goes to `/api/evaluate`; the same tag twice is one question."""
        assert evals('(§ v §) and (§ v §) and (§ w §)', 'dgs-md') == ['(§ v §)', '(§ w §)']

    def test_a_gnuplot_script_evaluates_its_tags(self, evals):
        assert evals("set title 'x'\nplot (§ tcold.mag §)\n", 'dgs-gnuplot') == \
            ['(§ tcold.mag §)']

    @pytest.mark.parametrize('mode', ['dgs-tex', 'dgs-yaml', 'dgs-md'])
    def test_nothing_evaluable_is_an_empty_list(self, evals, mode):
        assert evals('nothing to see here\n', mode) == []
