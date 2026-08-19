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

from core.audit.checks import (RE_FIGURE, RE_LABEL, blocks_of, magnitudes,
                               strip_maths_whitespace, RE_TAG)
from core.audit.sources import link_language

#: Worst first. A scope's column is as bad as its worst problem, so the order is the ranking.
STATES = ('broken', 'missing', 'partial', 'ok', 'none')

#: The file a statement lives in, and the one a solution lives in. `answer.md` sits beside the unit
#: rather than in a language directory, so it is not part of the translation status.
TRANSLATED = ('problem.md', 'solution.md')


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

def translation_status(unit, expected_languages):
    """
    Per language, whether each translated file is written, absent, empty, or still a mirror.

    `expected_languages` comes from the volume rather than the problem: a language the rest of the
    volume has and this problem does not is the interesting case, and the problem alone cannot know.
    """
    per_language = {}
    for lang in sorted(set(expected_languages) | set(unit.translated)):
        files = unit.translated.get(lang)
        if files is None:
            per_language[lang] = {'state': 'missing', 'note': 'no directory'}
            continue
        entries = {}
        for name in TRANSLATED:
            link = unit.links.get(f'{lang}/{name}')
            if link is not None:
                target = link_language(link) or link
                entries[name] = {'state': 'symlink', 'note': f'mirrors {target}'}
            elif name not in files:
                entries[name] = {'state': 'missing', 'note': 'absent'}
            elif not files[name].strip():
                entries[name] = {'state': 'empty', 'note': 'file is empty'}
            else:
                entries[name] = {'state': 'ok', 'note': ''}
        # `problem.md` absent is worse than `solution.md` absent: a volume with untranslated
        # solutions still runs, a volume with untranslated statements does not.
        state = ('missing' if entries['problem.md']['state'] == 'missing'
                 else 'ok' if all(e['state'] == 'ok' for e in entries.values())
                 else 'partial')
        per_language[lang] = {'state': state, 'note': '', 'files': entries}

    counts = Counter(v['state'] for v in per_language.values())
    if not per_language:
        return Status('translations', 'none', 'not translated at all')
    if counts['ok'] == len(per_language):
        return Status('translations', 'ok', f"{counts['ok']} languages complete",
                      {'languages': per_language})
    parts = [f"{n} {state}" for state, n in counts.most_common() if state != 'ok']
    if counts['ok']:
        parts.insert(0, f"{counts['ok']} complete")
    return Status('translations', 'missing' if counts['missing'] else 'partial',
                  ', '.join(parts), {'languages': per_language})


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
            labelled.setdefault(key, {}).setdefault(body, []).append(unit.label(lang, name))

    duplicated = {k: v for k, v in labelled.items()
                  if sum(len(places) for places in v.values()) > 1}
    identical = {k for k, v in duplicated.items() if len(v) == 1}
    divergent = set(duplicated) - identical

    detail = {'hoisted': sorted(hoisted), 'inline': sorted(labelled),
              'duplicated': sorted(duplicated), 'divergent': sorted(divergent)}
    if not hoisted and not labelled:
        return Status('equations', 'none', 'no labelled equations', detail)
    if not duplicated:
        return Status('equations', 'ok',
                      f"{len(hoisted)} in eq:, nothing written out twice", detail)
    if divergent:
        # copies differ by more than whitespace or a full stop, so hoisting is not mechanical
        return Status('equations', 'partial',
                      f"{len(hoisted)} in eq:, {len(identical)} could be hoisted, "
                      f"{len(divergent)} differ between languages", detail)
    return Status('equations', 'missing' if not hoisted else 'partial',
                  f"{len(hoisted)} in eq:, {len(identical)} written out twice and identical",
                  detail)


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
    Whether the numbers a statement shares across its translations are named in `values:`.

    A number that appears in *every* translation is a parameter of the problem; one that appears in
    only some is either a translation slip or something incidental, and either way not evidence for
    extraction. A problem whose statement has no numbers at all is `none`, not `missing`.
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

    detail = {'named': named, 'literal': sorted(shared), 'tagged': tagged}
    if not shared:
        if named:
            return Status('values', 'ok', f"{len(named)} named, nothing left literal", detail)
        return Status('values', 'none',
                      'no number appears in every translation' if len(statements) > 1
                      else 'no numbers in the statement', detail)
    if named or tagged:
        return Status('values', 'partial',
                      f"{len(named)} named, {len(shared)} still written out", detail)
    return Status('values', 'missing', f"{len(shared)} shared numbers, none named", detail)


# --- all of them ------------------------------------------------------------

def statuses(sources):
    """Every status for every unit: unit path -> kind -> Status."""
    languages = sorted({lang for unit in sources.unit_list for lang in unit.translated})
    return {
        unit.path: {
            s.kind: s for s in (
                translation_status(unit, languages),
                equation_status(unit),
                picture_status(unit),
                value_status(unit),
            )
        }
        for unit in sources.unit_list
    }
