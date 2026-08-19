r"""
Per-problem status: not "what is wrong" but "how far along is this".

The checks in `core.audit.checks` answer the first question and are the right shape for a defect --
one finding, one place, one message. These answer the second, which a table column wants instead: a
verdict per problem for each of the four things that take a volume from converted-on-paper to
actually finished.

    translations   is every language present, written, and not still mirroring its master
    equations      is a display equation that appears twice hoisted into `eq:`
    pictures       is every picture that exists actually included, and every inclusion resolvable
    values         are the numbers a statement shares across its translations named in `values:`

Five states, ordered worst first so a column sorts usefully. `NONE` is not a complaint: a problem
with no pictures has nothing to include, and saying "n/a" is the honest answer.
"""
import re
from collections import Counter
from dataclasses import dataclass, field

from core.audit.checks import (ANSWER_FILES, RE_EQ_KEY, RE_FIGURE, RE_LABEL, blocks_of, magnitudes,
                               strip_maths_whitespace, RE_TAG)
from core.audit.sources import link_language

#: Worst first. A scope's column is as bad as its worst problem, so the order is the ranking.
STATES = ('broken', 'missing', 'partial', 'ok', 'none')

#: The two files whose absence means "not translated". The other translatable files that
#: `module.mk` defines -- `problem-extra.md`, `answer-extra.md` -- are extra content only some
#: problems carry, so a language lacking one is a gap to show, not a translation that is missing.
#: Which files exist at all is `module.mk`'s business, carried on `Sources`; which of them a
#: translation is judged on is this decision.
TRANSLATED = ('problem.md', 'solution.md')

#: What one translated file can be. Not `STATES`: those rank a whole problem, these say what
#: happened to one file. `symlink` is not a fault -- a translation nobody has written yet mirrors
#: its master rather than keeping a stale copy -- but it is not a translation either, and the
#: table has to be able to say which.
TRANSLATION_STATES = ('ok', 'symlink', 'empty', 'missing')


@dataclass(frozen=True, slots=True)
class Status:
    """One verdict, with enough detail to explain itself in a tooltip."""
    kind: str
    state: str
    summary: str
    detail: dict = field(default_factory=dict)


def worst(states):
    """The worst of several states, ignoring `none` unless everything is `none`."""
    real = [s for s in states if s != 'none']
    if not real:
        return 'none'
    return min(real, key=STATES.index)


# --- translations -----------------------------------------------------------

def translation_status(unit, expected_languages, translated_files=TRANSLATED):
    """
    Per language, whether each translated file is written, absent, empty, or still a mirror.

    `expected_languages` comes from the volume rather than the problem: a language the rest of the
    volume has and this problem does not is the interesting case, and the problem alone cannot know.
    """
    # The files the module's build rules define, in their order, plus anything on disk that they do
    # not -- an unexpected file is exactly the thing a table should not hide. `problem.md` and
    # `solution.md` decide the verdict; the rest is extra content only some problems carry, and a
    # language lacking one is a gap to show rather than a translation that is missing.
    found = {name for files in unit.translated.values() for name in files}
    found |= {n.split('/', 1)[1] for n in unit.links if '/' in n}
    order = [n for n in translated_files if n in found or n in TRANSLATED]
    order += sorted(found - set(order))

    per_language = {}
    for lang in sorted(set(expected_languages) | set(unit.translated)):
        files = unit.translated.get(lang)
        if files is None:
            per_language[lang] = {'state': 'missing', 'note': 'no directory'}
            continue
        entries = {}
        for name in order:
            link = unit.links.get(f'{lang}/{name}')
            required = name in TRANSLATED
            if link is not None:
                # the target language when the link mirrors one, which is what a two-character cell
                # can show; anything else keeps its path in the note and shows no target
                mirrored = link_language(link)
                entry = {'state': 'symlink', 'language': mirrored,
                         'note': f'mirrors {mirrored or link}'}
            elif name not in files:
                entry = {'state': 'missing', 'note': 'absent'}
            elif not files[name].strip():
                entry = {'state': 'empty', 'note': 'file is empty'}
            else:
                entry = {'state': 'ok', 'note': ''}
            entries[name] = entry | {'required': required}
        # The verdict is the required files only. An optional extra one language carries and
        # another does not is real, but it is `presence`'s finding to report -- `trans` answers
        # "is this problem translated", and an answer sheet extra does not change that answer.
        required_states = [e['state'] for name, e in entries.items() if e['required']]
        state = ('missing' if entries['problem.md']['state'] == 'missing'
                 else 'ok' if all(s == 'ok' for s in required_states)
                 else 'partial')
        per_language[lang] = {'state': state, 'note': '', 'files': entries}

    counts = Counter(v['state'] for v in per_language.values())
    if not per_language:
        return Status('translations', 'none', 'not translated at all')
    if counts['ok'] == len(per_language):
        return Status('translations', 'ok', f"{counts['ok']} languages complete",
                      {'languages': per_language, 'order': order})
    parts = [f"{n} {state}" for state, n in counts.most_common() if state != 'ok']
    if counts['ok']:
        parts.insert(0, f"{counts['ok']} complete")
    return Status('translations', 'missing' if counts['missing'] else 'partial',
                  ', '.join(parts), {'languages': per_language, 'order': order})


def shared_file_states(unit, shared_files):
    """
    The files that sit beside the unit rather than in a language directory -- `answer.md` and the
    rest of `module.mk`'s `NABOJ_NONTRANSLATABLE` family. One per problem, not one per language, so
    there is no verdict here: most problems carry `answer.md` and nothing else, and an absent
    `answer-interval.md` is the normal case rather than a gap.
    """
    order = [n for n in shared_files if n in unit.shared or n in unit.links]
    order += sorted({n for n in unit.shared if n not in order and n not in shared_files})
    out = {}
    for name in order:
        link = unit.links.get(name)
        if link is not None:
            out[name] = {'state': 'symlink', 'language': link_language(link),
                         'note': f'mirrors {link}'}
        elif name not in unit.shared:
            out[name] = {'state': 'missing', 'note': 'absent'}
        elif not unit.shared[name].strip():
            out[name] = {'state': 'empty', 'note': 'file is empty'}
        else:
            out[name] = {'state': 'ok', 'note': ''}
    return out


# --- equation de-duplication ------------------------------------------------

def equation_status(unit):
    """
    Whether an equation that appears in more than one file has been hoisted into `eq:`.

    An equation written out once is not duplication and needs no `eq:` entry, so a problem with one
    solution is `none` rather than `missing` -- volumes 19 and 23 have Slovak solutions only and
    there is nothing there to de-duplicate.
    """
    hoisted = list((unit.meta or {}).get('eq') or {})
    labelled = {}
    for lang, name, text in unit.files():
        for m in blocks_of(text):
            label = RE_LABEL.search(m['tail'] or '')
            if not label or not label['name'].startswith(f'{unit.name}:'):
                continue
            key = label['name'].split(':', 1)[1]
            body = strip_maths_whitespace(m['body']).rstrip('.,;:!?')
            # real files, not language paths: see `Unit.real_label`
            places = labelled.setdefault(key, {}).setdefault(body, set())
            places.add(unit.real_label(lang, name))

    duplicated = {k: v for k, v in labelled.items()
                  if len({p for places in v.values() for p in places}) > 1}
    # Three reasons a duplicate is still a duplicate, and they are not the same problem:
    # `identical` can be hoisted mechanically; `divergent` needs somebody to decide which version is
    # right; `unnameable` is identical everywhere and still cannot be hoisted, because the key
    # becomes the label and `eq.stone-x` is not something Jinja can read.
    same = {k for k, v in duplicated.items() if len(v) == 1}
    identical = {k for k in same if RE_EQ_KEY.match(k)}
    unnameable = same - identical
    divergent = set(duplicated) - same

    detail = {'hoisted': sorted(hoisted), 'inline': sorted(labelled),
              'duplicated': sorted(duplicated), 'divergent': sorted(divergent),
              'unnameable': sorted(unnameable)}
    if not hoisted and not labelled:
        return Status('equations', 'none', 'no labelled equations', detail)
    if not duplicated:
        return Status('equations', 'ok',
                      f"{len(hoisted)} in eq:, nothing written out twice", detail)
    parts = [f"{len(hoisted)} in eq:"]
    if identical:
        parts.append(f"{len(identical)} written out twice and identical")
    if divergent:
        # copies differ by more than whitespace or a full stop, so hoisting is not mechanical
        parts.append(f"{len(divergent)} differ between languages")
    if unnameable:
        parts.append(f"{len(unnameable)} identical but the label is not a usable key")
    if not identical:
        # nothing mechanical left to do here, whatever else is outstanding
        return Status('equations', 'partial', ', '.join(parts), detail)
    return Status('equations', 'missing' if not hoisted else 'partial',
                  ', '.join(parts), detail)


# --- pictures ---------------------------------------------------------------

RE_INSERT_PICTURE = re.compile(r'\\insertPicture')
PICTURE_SUFFIXES = ('.svg', '.png', '.jpg', '.jpeg', '.pdf', '.gp', '.tikz')


def picture_status(unit):
    """
    Whether the pictures that exist are properly included, and every inclusion resolves.

    "Properly" means a Markdown figure with an attribute block: `convertor.py` rewrites that into
    `\\insertPicture` itself, and refuses an image with no attributes because pandoc wraps it in a
    `\\pandocbounded` that does not exist in the fragments this pipeline emits.
    """
    pictures = {a for a in unit.assets if a.lower().endswith(PICTURE_SUFFIXES)}
    stems = {p.rsplit('.', 1)[0] for p in pictures}
    referenced, unsized, broken, misnamed, hand_written = set(), [], [], [], []
    for lang, name, text in unit.files():
        where = unit.label(lang, name)
        for m in RE_FIGURE.finditer(text):
            target = m['file'].split()[0]
            referenced.add(target)
            if not (unit.root / target).exists():
                # A reference to `x.pdf` where the repository holds `x.svg` still resolves: make
                # converts `source/**.svg` into `build/**.pdf`. So it is not broken, but it is not
                # right either -- the source should name the source file, which is what
                # `convertor.py` assumes when it rewrites `\includegraphics` itself.
                if target.rsplit('.', 1)[0] in stems:
                    misnamed.append(f'{where}: {target}')
                else:
                    broken.append(f'{where}: {target}')
            if not text[m.end():m.end() + 1] == '{':
                unsized.append(f'{where}: {target}')
        if RE_INSERT_PICTURE.search(text):
            hand_written.append(where)

    # A picture may be included under a built name: `x.gp` becomes `x.pdf`. Count a picture as used
    # if anything with its stem is referenced.
    referenced_stems = {r.rsplit('.', 1)[0] for r in referenced}
    unused = sorted(p for p in pictures if p.rsplit('.', 1)[0] not in referenced_stems)

    detail = {'pictures': sorted(pictures), 'referenced': sorted(referenced),
              'unused': unused, 'broken': broken, 'misnamed': misnamed,
              'unsized': unsized, 'hand_written': hand_written}
    if not pictures and not referenced:
        return Status('pictures', 'none', 'no pictures', detail)
    if broken or hand_written:
        parts = []
        if broken:
            parts.append(f"{len(broken)} reference a file that does not exist")
        if hand_written:
            parts.append(rf"{len(hand_written)} use \insertPicture")
        return Status('pictures', 'broken', ', '.join(parts), detail)
    if unused or unsized or misnamed:
        parts = []
        if misnamed:
            parts.append(f"{len(misnamed)} name the built file, not the source")
        if unused:
            parts.append(f"{len(unused)} never included")
        if unsized:
            parts.append(f"{len(unsized)} without a size")
        return Status('pictures', 'partial', ', '.join(parts), detail)
    return Status('pictures', 'ok', f"{len(pictures)} included", detail)


# --- values -----------------------------------------------------------------

def value_status(unit):
    """
    Whether this problem's numbers are named rather than typed -- the ones it is given, and the one
    it produces.

    A number that appears in *every* translation of the statement is a parameter of the problem; one
    that appears in only some is either a translation slip or something incidental, and either way
    not evidence for extraction. A problem whose statement has no numbers at all is `none`, not
    `missing`.

    The answer file counts too. It holds the result, so a number typed there is a number nothing
    computes, and it can drift from the `values:` the solution derives it from. `answer-literal`
    reports that per problem; this folds it into the verdict, so a problem whose statement is fully
    extracted but whose answer is still typed reads `partial` rather than `ok`.
    """
    statements = {lang: files['problem.md'] for lang, files in unit.translated.items()
                  if 'problem.md' in files}
    named = list((unit.meta or {}).get('values') or {})
    if not statements:
        return Status('values', 'none', 'no statement to read', {'named': named})

    shared = None
    for text in statements.values():
        here = set(magnitudes(text))
        shared = here if shared is None else (shared & here)
    shared = shared or set()
    tagged = any(RE_TAG.search(text) for text in statements.values())

    # the answer file: a number there is the result, and a result should be computed
    answer = {name: text for name in ANSWER_FILES
              if (text := unit.shared.get(name)) and text.strip()}
    typed_answer = [name for name, text in answer.items()
                    if not RE_TAG.search(text) and magnitudes(text)]

    detail = {'named': named, 'literal': sorted(shared), 'tagged': tagged,
              'typed_answer': sorted(typed_answer)}
    if not shared:
        if typed_answer:
            return Status('values', 'partial',
                          f"{len(named)} named, but {', '.join(typed_answer)} "
                          f"{'is' if len(typed_answer) == 1 else 'are'} typed out", detail)
        if named:
            return Status('values', 'ok', f"{len(named)} named, nothing left literal", detail)
        return Status('values', 'none',
                      'no number appears in every translation' if len(statements) > 1
                      else 'no numbers in the statement', detail)
    also = f", and {', '.join(typed_answer)} typed" if typed_answer else ''
    if named or tagged:
        return Status('values', 'partial',
                      f"{len(named)} named, {len(shared)} still written out{also}", detail)
    return Status('values', 'missing',
                  f"{len(shared)} shared numbers, none named{also}", detail)


# --- all of them ------------------------------------------------------------

def statuses(sources):
    """Every status for every unit: unit path -> kind -> Status."""
    languages = sorted({lang for unit in sources.unit_list for lang in unit.translated})
    return {
        unit.path: {
            s.kind: s for s in (
                translation_status(unit, languages, sources.translated_files),
                equation_status(unit),
                picture_status(unit),
                value_status(unit),
            )
        }
        for unit in sources.unit_list
    }
