r"""
The source-only checks: every sweep that had to be written by hand while auditing volumes 19 to 29,
made permanent and made correct.

Each is a function over a scope's `Sources` yielding `Finding`s. No writing, no subprocesses -- the
whole point of this layer is that it costs a fifth of a second over the entire repository, so the
overview page can recompute everything on every request.

Several checks carry a comment naming a false positive they must *not* produce. Those are not
hypothetical: each one was produced by the first version of that sweep and cost real time. They are
tested in `core/tests/test_audit.py`.

`core` importing `modules` is backwards, so the two naboj-specific checks import their vocabulary
lazily and declare `modules=('naboj',)`; nothing here needs `modules` to be importable otherwise.
"""
import re
from collections import Counter, defaultdict

from core.audit.model import Finding, check

# --- shared patterns --------------------------------------------------------

#: A display block: `$$` or `$${` on its own line, body, `$$` or `}$$`, optionally then a label.
#: Anchored at the line start, which is why `delimiter-indented` has to run first -- see below.
RE_BLOCK = re.compile(
    r'^\$\$(?P<open>\{?)[ \t]*\n(?P<body>.*?)^(?P<close>\}?)\$\$[ \t]*(?P<tail>[^\n]*)',
    re.S | re.M)

#: `\left` and `\right` only when a delimiter follows. Two traps in one line: `\rightarrow`
#: contains `\right`, and `\right` is a control word, so TeX skips whitespace -- including a
#: newline -- before its delimiter. Matching `\\right(?=[)\]}])` reports both as errors.
RE_LEFT = re.compile(r'\\left\s*(?=[([{|.\\])')
RE_RIGHT = re.compile(r'\\right\s*(?=[)\]}|.\\])')

#: A label definition and a crossref. Both `[@x]` and `[-@x]` are references.
RE_LABEL = re.compile(r'\{#(?P<kind>eq|fig|tbl|sec):(?P<name>[^}\s]+)')
RE_REF = re.compile(r'@(?P<kind>eq|fig|tbl|sec):(?P<name>[\w:.\-]+)')

#: A Jinja tag. Stripped before comparing numbers: a tag is by definition the same everywhere.
RE_TAG = re.compile(r'\(§.*?§\)')

#: siunitx macros carrying a magnitude, and how many brace groups each takes -- the last of which
#: is the unit, where there is one. Getting the arity wrong is not harmless: reading
#: `\qtyrange{0}{30}{\celsius}` as if it were `\qty` makes `30` look like a unit written as text.
SI_ARITY = {
    'num': (1, None), 'ang': (1, None), 'numlist': (1, None), 'numrange': (2, None),
    'qty': (2, 1), 'qtylist': (2, 1), 'qtyrange': (3, 2),
}

#: The option group is not optional to allow: the first version of this omitted it, so every
#: `\qty[per-mode=symbol]{200}{...}` was invisible and the cross-language comparison reported
#: disagreements that were not disagreements.
RE_SI_HEAD = re.compile(r'\\(?P<macro>qtyrange|qtylist|numrange|numlist|qty|num|ang)'
                        r'(?P<opts>\[[^\]]*\])?(?=\{)')
RE_NUMBER = re.compile(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?')


class SICall:
    """One siunitx call, with its arguments separated by arity rather than by position."""
    __slots__ = ('macro', 'opts', 'args', 'start', 'text')

    def __init__(self, macro, opts, args, start, text):
        self.macro, self.opts, self.args, self.start, self.text = macro, opts, args, start, text

    @property
    def unit(self):
        _, unit_at = SI_ARITY[self.macro]
        return self.args[unit_at] if unit_at is not None and unit_at < len(self.args) else None

    @property
    def values(self):
        _, unit_at = SI_ARITY[self.macro]
        return [a for i, a in enumerate(self.args) if i != unit_at]

    @property
    def magnitudes(self):
        return [n for value in self.values for n in RE_NUMBER.findall(value)]


def _brace_group(text, i):
    r"""
    The `{...}` at or after `i`, tolerating nesting. (end, contents) or None.

    Whitespace before the brace is skipped, because TeX skips it: `\qty{10} {\centi\metre}` and
    `\qty{0.3}` with its unit on the next line are both single calls, and a parser that insists on
    an adjacent brace reads them as having no unit -- which made two Russian statements look as
    though they were missing a number.
    """
    while i < len(text) and text[i] in ' \t\n':
        i += 1
    if i >= len(text) or text[i] != '{':
        return None
    depth, j = 0, i
    while j < len(text):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                return j + 1, text[i + 1:j]
        j += 1
    return None


def si_calls(text):
    """Every siunitx call in the text, parsed with the right number of arguments."""
    for head in RE_SI_HEAD.finditer(text):
        arity, _ = SI_ARITY[head['macro']]
        args, i = [], head.end()
        for _ in range(arity):
            group = _brace_group(text, i)
            if group is None:
                break
            i, contents = group
            args.append(contents)
        if len(args) == arity:
            yield SICall(head['macro'], head['opts'] or '', args, head.start(), text)

#: `\text{...}` and friends inside a unit argument: text wrapped in a macro is still text, and
#: siunitx refuses it exactly as it refuses bare text. `chem/01/zaklínač` writes
#: `\qty{522}{\text{ľudí}}` and the Slovak solutions target would not compile because of it.
RE_TEXT_WRAPPER = re.compile(r'\\(?:text|textrm|mathrm|mathit|mbox)\{[^{}]*\}')


#: A macro name, and a brace group. Removing both from a unit argument leaves whatever siunitx
#: would have to read as literal text.
RE_MACRO = re.compile(r'\\[a-zA-Z]+')
RE_BRACES = re.compile(r'[{}]')


def literal_unit(argument):
    r"""
    Whether a unit argument is text rather than units.

    `core/latex/siunitx.tex` sets `forbid-literal-units = true`, so any of these is a hard error
    unless the call passes `forbid-literal-units=false`.

    Three shapes, and the third is why this is not just "does it contain a backslash":

        km                      bare text
        \text{ľudí}              text wrapped in a macro -- still text
        rok\tothe{-1}            text *mixed with* a real macro

    A genuine unit argument is macros all the way down, so strip the macro names and the braces and
    see whether any letters are left. `chem/01` had one of each of the last two, and both of them
    kept its solutions from compiling.
    """
    if RE_TEXT_WRAPPER.search(argument):
        return True
    remainder = RE_BRACES.sub('', RE_MACRO.sub('', argument))
    return any(c.isalpha() for c in remainder)

#: `\\` is a row break. Followed by letters it is a row break plus the letters, set in maths
#: italic -- `\\QQText{és}` typesets "QQText".
RE_DOUBLE_MACRO = re.compile(r'(?<!\\)\\\\([A-Za-z]{2,})')

#: A markdown figure with an attribute block.
RE_FIGURE = re.compile(r'!\[[^\]]*\]\((?P<file>[^)]+)\)')

MATH_MACROS_WITH_TEXT = re.compile(r'\\(?:text|QQText|QText|operatorname)\{[^{}]*\}')


def strip_maths_whitespace(s):
    """
    Whitespace removed everywhere except inside `\\text{}`-like macros, where it is real text.

    TeX ignores whitespace in maths mode entirely, so `\\frac{1}{2^nk}` and `\\frac{1}{2^n k}` are
    the same equation and a body spread over twelve lines is the same as one on two.
    """
    out, last = [], 0
    for m in MATH_MACROS_WITH_TEXT.finditer(s):
        out.append(re.sub(r'\s+', '', s[last:m.start()]))
        out.append(m[0])
        last = m.end()
    out.append(re.sub(r'\s+', '', s[last:]))
    return ''.join(out)


def ignored(unit, check_id):
    """
    Whether a problem opts out of a check, via `audit: {ignore: [...]}` in its meta.

    Needed because some findings are the point of the problem: `23/grammar-nazi` is deliberately
    misspelled, and `23/bats`, `27/escalator` and `28/john-doe` have invented units.
    """
    if not unit.meta:
        return False
    spec = unit.meta.get('audit') or {}
    return check_id in (spec.get('ignore') or [])


def blocks_of(text):
    """Display blocks, or nothing at all if the file's delimiters cannot be trusted."""
    if RE_DELIMITER_INDENTED.search(text):
        return []
    return list(RE_BLOCK.finditer(text))


#: A delimiter indented by one to three spaces. Pandoc accepts it, but every tool that anchors on
#: `^$$` then pairs one block's *closing* delimiter with the next block's opener and treats the
#: prose between them as maths. Found in `21/split-capacitor/hu` and `27/pendula/hu`, where it had
#: silently kept the latter unhoistable; a first attempt at re-indenting turned two Hungarian
#: paragraphs into a verbatim block because of it.
RE_DELIMITER_INDENTED = re.compile(r'^[ ]{1,3}\}?\$\$', re.M)


def line_of(text, offset):
    return text.count('\n', 0, offset) + 1


# --- metadata ---------------------------------------------------------------

@check('meta-missing', 'error', 'No meta.yaml at all')
def meta_missing(sources):
    for unit in sources.unit_list:
        if unit.meta_raw is None:
            yield Finding('meta-missing', 'error', 'the problem has no meta.yaml', unit.path)


@check('meta-empty', 'error', 'meta.yaml is empty')
def meta_empty(sources):
    for unit in sources.unit_list:
        if unit.meta_raw is not None and not unit.meta_raw.strip():
            yield Finding('meta-empty', 'error', 'meta.yaml is a zero-byte file', unit.path)


@check('meta-unparseable', 'error', 'meta.yaml does not parse')
def meta_unparseable(sources):
    for unit in sources.unit_list:
        if unit.meta_error:
            yield Finding('meta-unparseable', 'error', unit.meta_error, unit.path, 'meta.yaml')


@check('meta-invalid', 'error', 'meta.yaml fails its schema', modules=('naboj',))
def meta_invalid(sources):
    # Lazily, because `core` importing `modules` is backwards and only this check needs it.
    from modules.naboj.builder.renderer import NabojStandaloneContext
    for unit in sources.unit_list:
        if unit.meta is None:
            continue                        # already reported by one of the three above
        try:
            NabojStandaloneContext._schema.validate(unit.meta | {'id': unit.name})
        except Exception as e:
            yield Finding('meta-invalid', 'error', str(e).splitlines()[-1][:160],
                          unit.path, 'meta.yaml')


#: What the repo writes when nobody is recorded. Not a name, so not an author.
UNRECORDED = {'?', ''}


def recorded_names(authors, role):
    """The real names in one role, with the explicit-unknown marker filtered out."""
    return [str(n) for n in (authors.get(role) or []) if str(n).strip() not in UNRECORDED]


@check('authors-empty', 'warning', 'Nobody recorded as an author', modules=('naboj',))
def authors_empty(sources):
    for unit in sources.unit_list:
        if not unit.meta:
            continue
        authors = unit.meta.get('authors')
        if isinstance(authors, dict) and not any(recorded_names(authors, role) for role
                                                 in ('idea', 'problem', 'solution')):
            yield Finding('authors-empty', 'warning', 'nobody is recorded in any of the three '
                                                     'roles', unit.path)


@check('author-placeholder', 'warning', 'A placeholder where a name belongs',
       modules=('naboj',))
def author_placeholder(sources):
    for unit in sources.unit_list:
        if not unit.meta:
            continue
        authors = unit.meta.get('authors')
        if not isinstance(authors, dict):
            continue
        for role, names in authors.items():
            for name in (names if isinstance(names, list) else [names]):
                # `?` is the repo's explicit-unknown marker, counted by `authors-empty`;
                # these would each be typeset as somebody's name
                if str(name).strip().lower() in ('unknown', '-', 'n/a', 'tbd', 'todo'):
                    yield Finding('author-placeholder', 'warning',
                                  f"authors.{role} holds {name!r}, which would be typeset as a "
                                  f"person's name", unit.path)


@check('tags-empty', 'warning', 'No tags', modules=('naboj',))
def tags_empty(sources):
    for unit in sources.unit_list:
        if unit.meta and not unit.meta.get('tags'):
            yield Finding('tags-empty', 'warning', 'the problem is untagged', unit.path)


@check('tag-unknown', 'warning', 'A tag outside the vocabulary', modules=('naboj',))
def tag_unknown(sources):
    from modules.naboj.builder.renderer import VALID_TAGS
    # Chemistry has no vocabulary of its own -- `VALID_TAGS` is physics -- so every chemistry tag
    # would be reported. Say it once at scope level instead of once per problem.
    if sources.scope.startswith('chem'):
        used = {t for u in sources.unit_list if u.meta for t in (u.meta.get('tags') or [])}
        if used - set(VALID_TAGS):
            yield Finding('tag-unknown', 'warning',
                          f"chemistry has no tag vocabulary of its own, so all "
                          f"{len(used - set(VALID_TAGS))} of its tags fall outside VALID_TAGS, "
                          f"which is physics")
        return
    for unit in sources.unit_list:
        for tag in (unit.meta or {}).get('tags') or []:
            if tag not in VALID_TAGS:
                yield Finding('tag-unknown', 'warning', f"{tag!r} is not in VALID_TAGS", unit.path)


# --- maths ------------------------------------------------------------------

@check('delimiter-indented', 'error', 'A display delimiter is indented')
def delimiter_indented(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in RE_DELIMITER_INDENTED.finditer(text):
                yield Finding('delimiter-indented', 'error',
                              'pandoc accepts it, but it mis-pairs every delimiter after it for '
                              'anything anchored on `^$$`, so the prose between two blocks reads '
                              'as maths',
                              unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('dollar-unpaired', 'error', 'Inline $ delimiters do not pair up')
def dollar_unpaired(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            stripped = re.sub(r'\\\$|\$\$', '', text)
            if stripped.count('$') % 2:
                # point at the offending line, which is the one with an odd count
                for i, line in enumerate(text.splitlines(), 1):
                    if re.sub(r'\\\$|\$\$', '', line).count('$') % 2:
                        yield Finding('dollar-unpaired', 'error',
                                      'from here on, maths and text are swapped',
                                      unit.path, unit.label(lang, name), i)
                        break


@check('left-right-unbalanced', 'error', r'\left without \right')
def left_right_unbalanced(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            left, right = len(RE_LEFT.findall(text)), len(RE_RIGHT.findall(text))
            if left != right:
                yield Finding('left-right-unbalanced', 'error',
                              f"{left} \\left against {right} \\right; xelatex stops with "
                              f"'Missing \\right. inserted'",
                              unit.path, unit.label(lang, name))


@check('block-indent', 'warning', 'A display block is not indented by four')
def block_indent(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in blocks_of(text):
                lines = [l for l in m['body'].split('\n') if l.strip()]
                if not lines:
                    continue
                least = min(len(l) - len(l.lstrip(' ')) for l in lines)
                if least != 4:
                    yield Finding('block-indent', 'warning',
                                  f"indented by {least}; `MathObject.disp` re-indents by exactly "
                                  f"four, so this block cannot be hoisted byte-neutrally",
                                  unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('aligned-longhand', 'warning', r'\begin{aligned} where $${ … }$$ is meant')
def aligned_longhand(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in blocks_of(text):
                if not m['open'] and r'\begin{aligned}' in m['body']:
                    yield Finding('aligned-longhand', 'warning',
                                  '`convertor.py` rewrites `$${` into `$$\\n\\begin{aligned}`, so '
                                  'the two give identical TeX -- but `MathObject` has a separate '
                                  'format spec for each, so the same equation in two spellings '
                                  'reads as two equations',
                                  unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('double-backslash-macro', 'error', r'\\ immediately followed by a macro name')
def double_backslash_macro(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in RE_DOUBLE_MACRO.finditer(text):
                yield Finding('double-backslash-macro', 'error',
                              f"`\\\\{m[1]}` is a row break followed by the letters {m[1]!r}, set "
                              f"in maths italic",
                              unit.path, unit.label(lang, name), line_of(text, m.start()))


# --- labels and references --------------------------------------------------

@check('label-schema', 'warning', 'A label outside <kind>:<problem>:<label>',
       modules=('naboj',))
def label_schema(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in RE_LABEL.finditer(text):
                label = m['name']
                if label == unit.name or label.startswith(f'{unit.name}:'):
                    continue
                yield Finding('label-schema', 'warning',
                              f"`{m['kind']}:{label}` does not name this problem; an `eq:` key is "
                              f"taken from the label, so the equation cannot be hoisted",
                              unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('reference-dangling', 'error', 'A crossref resolving to nothing',
       modules=('naboj',))
def reference_dangling(sources):
    # A hoisted equation defines its label in `meta.yaml`, not in any source, so the label set has
    # to include the `eq:` keys -- otherwise every hoisted equation looks like a broken reference.
    labels = set()
    for unit in sources.unit_list:
        for _, _, text in unit.files():
            labels |= {f"{m['kind']}:{m['name']}" for m in RE_LABEL.finditer(text)}
        for key in ((unit.meta or {}).get('eq') or {}):
            labels.add(f'eq:{unit.name}:{key}')
        # The templates emit \label{sec:<problem>:problem} and :solution for every problem, so a
        # section reference to any problem in the scope resolves at build time.
        labels |= {f'sec:{unit.name}:problem', f'sec:{unit.name}:solution'}
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in RE_REF.finditer(text):
                ref = f"{m['kind']}:{m['name']}"
                if ref not in labels:
                    yield Finding('reference-dangling', 'error',
                                  f"`@{ref}` matches no label anywhere in the volume",
                                  unit.path, unit.label(lang, name), line_of(text, m.start()))


# --- translations -----------------------------------------------------------

def magnitudes(text):
    """The bare magnitudes in a text, Jinja tags removed. A tag is the same in every language."""
    counter = Counter()
    for call in si_calls(RE_TAG.sub('', text)):
        counter.update(call.magnitudes)
    return counter


@check('unit-unlisted', 'error',
       'A problem directory the volume meta does not name', modules=('naboj',))
def unit_unlisted(sources):
    """
    A problem the volume's `problems:` list omits. `ContextVolume` iterates that list, so the
    directory is read by nothing and reaches no PDF -- the problem simply is not in the competition.
    Adding it is not mechanical: it changes what a past round contained and renumbers what follows,
    so this reports and stops there.
    """
    if not sources.listed_order:
        return                      # nothing to be unlisted against
    for unit in sources.unlisted:
        yield Finding('unit-unlisted', 'error',
                      f"not in {sources.scope}/meta.yaml's `problems:`, so it is never built",
                      unit.path)


@check('listed-missing', 'error',
       'The volume meta names a problem that has no directory', modules=('naboj',))
def listed_missing(sources):
    """
    The other direction: the list names a problem that is not there.

    `\\protectedInput` puts a red `Missing file ...!` box in the page, which is exactly right --
    a hole in a booklet should be impossible to miss, not a silent gap. The check earns its keep
    upstream of that: it names the stale entry from the sources, so nobody has to compile a volume
    and read 46 pages to find out. Volume 19 carried `onion` for years after the directory became
    `onion-capacity`.
    """
    for name in sources.missing_from_disk:
        yield Finding('listed-missing', 'error',
                      f"`{name}` is listed in {sources.scope}/meta.yaml but no such directory "
                      f"exists; the page will carry a `Missing file` box in its place")


@check('translation-set', 'warning',
       'A problem with different languages from its neighbours', modules=('naboj',))
def translation_set(sources):
    sets = {u.path: frozenset(u.languages) for u in sources.unit_list if u.languages}
    if len(sets) < 2:
        return
    norm = Counter(sets.values()).most_common(1)[0][0]
    for path, langs in sorted(sets.items()):
        if langs != norm:
            missing = sorted(norm - langs)
            extra = sorted(langs - norm)
            parts = []
            if missing:
                parts.append(f"missing {' '.join(missing)}")
            if extra:
                parts.append(f"has {' '.join(extra)} that others do not")
            yield Finding('translation-set', 'warning', '; '.join(parts), path)


@check('presence', 'warning', 'A file some languages have and others do not',
       modules=('naboj',))
def presence(sources):
    for unit in sources.unit_list:
        if len(unit.languages) < 2:
            continue
        names = {n for files in unit.translated.values() for n in files}
        for name in sorted(names):
            have = [l for l in unit.languages if name in unit.translated[l]]
            if len(have) != len(unit.languages):
                yield Finding('presence', 'warning',
                              f"{name} in {' '.join(have)} but not "
                              f"{' '.join(l for l in unit.languages if l not in have)}",
                              unit.path)


@check('magnitude-disagreement', 'warning', 'Translations disagree on a number',
       modules=('naboj',))
def magnitude_disagreement(sources):
    for unit in sources.unit_list:
        per_lang = {}
        for lang in unit.languages:
            text = unit.translated[lang].get('problem.md')
            if text is not None:
                per_lang[lang] = magnitudes(text)
        if len(per_lang) < 2 or len({tuple(sorted(c.items())) for c in per_lang.values()}) == 1:
            continue
        every = set().union(*(set(c) for c in per_lang.values()))
        for number in sorted(every):
            have = sorted(l for l, c in per_lang.items() if c.get(number))
            if len(have) == len(per_lang):
                continue
            lacking = [l for l in sorted(per_lang) if l not in have]
            yield Finding('magnitude-disagreement', 'warning',
                          f"{number} appears in {' '.join(have)} but not in "
                          f"{' '.join(lacking)}", unit.path)


@check('hardcoded-value', 'warning',
       'A number spelled out where another language uses a tag', modules=('naboj',))
def hardcoded_value(sources):
    """
    The master takes a quantity from `values:` and a translation writes the number out. That is how
    a translation comes to disagree with its master about a parameter, which is the whole reason
    `values:` exists.
    """
    for unit in sources.unit_list:
        if not (unit.meta or {}).get('values'):
            continue
        tagged, literal = [], []
        for lang in unit.languages:
            text = unit.translated[lang].get('problem.md')
            if text is None:
                continue
            (tagged if RE_TAG.search(text) else literal).append(lang)
        if tagged and literal and magnitudes(''.join(
                unit.translated[l].get('problem.md', '') for l in literal)):
            yield Finding('hardcoded-value', 'warning',
                          f"{' '.join(tagged)} read the quantities from `values:`; "
                          f"{' '.join(literal)} spell numbers out instead", unit.path)


# --- siunitx ----------------------------------------------------------------

@check('literal-unit', 'error', 'A unit written as text')
def literal_unit_check(sources):
    """
    `core/latex/siunitx.tex` sets `forbid-literal-units = true`, so text where a unit macro belongs
    is a hard error -- "Package siunitx Error: Literal units disabled." -- not merely unidiomatic.
    An invented unit is fine if the call says so; there is no `allow-literal-units` in siunitx v3.
    """
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for call in si_calls(text):
                arg = call.unit
                if not arg or '§' in arg or not literal_unit(arg):
                    continue
                if 'forbid-literal-units=false' in call.opts:
                    continue
                yield Finding('literal-unit', 'error',
                              f"`{arg}` is text where a unit macro belongs; pass "
                              f"`forbid-literal-units=false` if it is deliberate",
                              unit.path, unit.label(lang, name), line_of(text, call.start))


@check('symbolic-number', 'error', 'A symbolic value without parse-numbers=false')
def symbolic_number(sources):
    """
    `\\qty` parses its first argument as a number. `\\qty{\\pi}{...}` fails with "Invalid number".
    Two things that look symbolic and are not: `\\qty{5730 \\pm 40}{...}` is an uncertainty, which
    `separate-uncertainty` handles, and `\\qty{e13}{...}` is a bare exponent meaning 10^13 -- valid,
    and the spelling this repo prefers.
    """
    numeric = re.compile(r'^[-+0-9.,eE\s]*$')
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for call in si_calls(text):
                if 'parse-numbers' in call.opts:
                    continue
                for value in call.values:
                    # a list argument is semicolon-separated, and every item must be a number
                    # a list is semicolon-separated, and so is `\ang`'s degrees-minutes-seconds form
                    items = (value.split(';')
                             if call.macro.endswith('list') or call.macro == 'ang'
                             else [value])
                    for item in items:
                        if '§' in item or numeric.match(item):
                            continue
                        # `\qty{5730 \pm 40}{...}` is an uncertainty, which `separate-uncertainty`
                        # handles, and `\ang{30;15;0}` is degrees-minutes-seconds
                        if re.fullmatch(r'[-+0-9.\s]*\\pm[-+0-9.\s]*', item):
                            continue
                        yield Finding('symbolic-number', 'error',
                                      f"`{item}` is not a number; siunitx refuses without "
                                      f"`parse-numbers=false`",
                                      unit.path, unit.label(lang, name),
                                      line_of(text, call.start))


# --- files ------------------------------------------------------------------

@check('insert-picture', 'error', r'\insertPicture written by hand')
def insert_picture(sources):
    r"""
    `convertor.py` rewrites pandoc's `\includegraphics` into `\insertPicture` *after* the TeX
    exists, so writing it in a source skips pandoc entirely. The macro also takes one bracketed
    optional argument, so the common `\insertPicture{x.pdf}{40mm}` never applies the size.
    """
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in re.finditer(r'\\insertPicture', text):
                yield Finding('insert-picture', 'error',
                              'the TeX command belongs in the output, not the source; write '
                              '`![](picture.svg){height=40mm}`',
                              unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('figure-built-name', 'warning', 'A figure naming the built file, not the source')
def figure_built_name(sources):
    """Registered so the id is known; both cases are yielded by `figure_missing`."""
    return ()


@check('figure-missing', 'error', 'A figure whose file exists nowhere')
def figure_missing(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in RE_FIGURE.finditer(text):
                target = m['file'].split()[0]
                if target.startswith(('http:', 'https:')):
                    continue
                if (unit.root / target).exists():
                    continue
                # `x.pdf` where the repository holds `x.svg` still resolves -- make converts
                # `source/**.svg` into `build/**.pdf` -- so that is a naming slip, not a hole.
                stems = {a.rsplit('.', 1)[0] for a in unit.assets}
                if target.rsplit('.', 1)[0] in stems:
                    yield Finding('figure-built-name', 'warning',
                                  f"{target} names the built file; the source holds "
                                  f"{target.rsplit('.', 1)[0]}.svg and that is what belongs here",
                                  unit.path, unit.label(lang, name), line_of(text, m.start()))
                else:
                    yield Finding('figure-missing', 'error',
                                  f"{target} exists nowhere in the problem; LaTeX falls back to "
                                  f"`example-image`",
                                  unit.path, unit.label(lang, name), line_of(text, m.start()))


#: `![](file.svg}` -- the target closed with a brace instead of a parenthesis. Pandoc does not read
#: this as an image at all, so the picture silently does not appear.
RE_FIGURE_MALFORMED = re.compile(r'!\[[^\]]*\]\([^)\n]*\}')


@check('figure-malformed', 'error', 'A figure whose target is not closed')
def figure_malformed(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in RE_FIGURE_MALFORMED.finditer(text):
                yield Finding('figure-malformed', 'error',
                              'the target is closed with `}` instead of `)`, so pandoc does not '
                              'read it as an image and the picture does not appear',
                              unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('figure-unsized', 'warning', 'A figure with no attribute block')
def figure_unsized(sources):
    """
    pandoc >= 3.2 wraps an image carrying no attributes in `\\pandocbounded`, which does not exist
    in the fragments this pipeline emits -- `convertor.py` refuses outright rather than defining it.
    """
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            for m in re.finditer(r'!\[[^\]]*\]\([^)]+\)(?!\{)', text):
                yield Finding('figure-unsized', 'warning',
                              'give it a size, e.g. `{height=40mm}`, or the convertor refuses it',
                              unit.path, unit.label(lang, name), line_of(text, m.start()))


@check('asset-unused', 'info', 'A picture nothing references')
def asset_unused(sources):
    for unit in sources.unit_list:
        referenced = set()
        for _, _, text in unit.files():
            referenced |= {m['file'].split()[0] for m in RE_FIGURE.finditer(text)}
        for asset in sorted(unit.assets):
            if asset.rsplit('/', 1)[-1].endswith(('.svg', '.png', '.jpg', '.pdf')) \
                    and asset not in referenced:
                yield Finding('asset-unused', 'info',
                              f"{asset} is referenced by no language", unit.path)


@check('symlink', 'info', 'A translation that is a symlink')
def symlink(sources):
    """
    Deliberate -- a translation nobody has written yet mirrors its master rather than keeping a
    stale copy -- and recorded because writing through one hits the same real file twice. 88 files
    were shredded that way once.
    """
    for unit in sources.unit_list:
        for link in sorted(unit.links):
            yield Finding('symlink', 'info', f"{link} is a symlink; resolve before writing",
                          unit.path, link)


@check('encoding', 'warning', 'CRLF, tabs or trailing whitespace')
def encoding(sources):
    for unit in sources.unit_list:
        for lang, name, text in unit.files():
            problems = []
            if '\r' in text:
                problems.append('CRLF line endings')
            if '\t' in text:
                problems.append('tabs')
            if any(line != line.rstrip() for line in text.split('\n')):
                problems.append('trailing whitespace')
            if problems:
                yield Finding('encoding', 'warning', ', '.join(problems),
                              unit.path, unit.label(lang, name))


# --- hoisting ---------------------------------------------------------------

#: An `eq:` key has to be a Python-ish identifier (`ValidIdentifier` in
#: `core/builder/context/context.py`), and it also has to survive Jinja's dot notation -- `eq.stone-x`
#: parses as `eq.stone - x`, so a hyphenated label cannot be referenced at all. Five of
#: `22/skateboard`'s labels are hyphenated, and suggesting a hoist that cannot be written is worse
#: than saying nothing.
RE_EQ_KEY = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')


@check('hoistable-equation', 'info', 'A labelled equation written out more than once')
def hoistable_equation(sources):
    """
    The same labelled block in more than one file is that many copies of one equation, and that is
    how they drift apart. Whitespace and a trailing full stop do not count as a difference: TeX
    ignores maths-mode whitespace, and `MathObject` carries the punctuation in its format spec.

    A label that could not become an `eq:` key is not reported: the key becomes the label, so
    hoisting it would have to rename it, which changes the label in the built page.
    """
    for unit in sources.unit_list:
        blocks = defaultdict(lambda: defaultdict(list))
        for lang, name, text in unit.files():
            for m in blocks_of(text):
                label = RE_LABEL.search(m['tail'] or '')
                if not label or not label['name'].startswith(f'{unit.name}:'):
                    continue
                key = label['name'].split(':', 1)[1]
                body = strip_maths_whitespace(m['body']).rstrip('.,;:!?')
                # by real file: a mirrored translation is the same bytes, so counting it again
                # would report `27/brakemaster` as seven copies of what is written five times
                place = unit.real_label(lang, name)
                if place not in blocks[key][body]:
                    blocks[key][body].append(place)
        for key, variants in sorted(blocks.items()):
            places = {p for group in variants.values() for p in group}
            if len(places) < 2:
                continue
            if not RE_EQ_KEY.match(key):
                continue
            if len(variants) == 1:
                yield Finding('hoistable-equation', 'info',
                              f"`{key}` is identical in {len(places)} files; it could be one "
                              f"`eq:` entry", unit.path, ' '.join(places))
            else:
                yield Finding('hoistable-equation', 'info',
                              f"`{key}` appears in {len(places)} files in {len(variants)} "
                              f"variants, so it cannot be hoisted as it stands",
                              unit.path, ' '.join(places))
