r"""
Built artefacts whose source is gone -- the one failure make says it cannot cure itself.

`Makefile:55-61` states it outright: *deleting* a source leaves its built counterpart behind,
because a target whose prerequisite has vanished has no rule left to remove it. `.SECONDARY:`
with no prerequisites (`Makefile:45`) then keeps every intermediate for ever, so nothing clears
up after a rename either.

Most of the time an orphan is only dead weight. It is a **wrong page** when the scope meta still
names the unit: `\protectedInput` finds the stale `.tex` and includes it, so the booklet prints
the problem that was deleted, or prints nothing where a red `Missing file` box was owed. That
case is an error, and `listed-missing` already reports it from the sources; this reports the
artefact, which is the half nobody can see.

**A unit directory or a language directory, and nothing coarser.** `build/` is full of directories with no source
counterpart by design -- `answers/`, `solutions/`, `build/core/`, every aggregate a template
produces -- and a rule that merely asks "is there a source directory of this name" calls 567 of
them stale. What makes a *unit* different is that the audit already knows where units live: the
scope's own unit paths give both the parent directory to look in and the set of names that
belong there. So the question asked here is the narrow one, **is there a directory beside the
units that is not a unit**, and it has no false positives to weigh against.

The limitation that follows, and it is worth knowing: a unit whose siblings are gone too is not
found, because the parent is no longer a place units live. A whole volume that moved --
`build/naboj/phys/00`, 161 files, from before the specimen volume became its own module -- is
invisible here and wants a human. Leaves are what renames produce, and leaves are what this
finds.
"""
from dataclasses import dataclass
from pathlib import Path

#: Both mirrors of `source/`, in pipeline order. `output/` is deliberately not one of them: a PDF
#: there is a deliverable somebody may have sent to a printer, not an intermediate.
STAGES = ('render', 'build')


@dataclass(frozen=True, slots=True)
class Orphan:
    """One built directory with no source left."""
    stage: str                  # 'render' or 'build'
    rel: str                    # path below the stage root, e.g. 'phys/pool/problems/old-name'
    path: Path                  # absolute
    files: int                  # how much is in there, for a report that says what it would cost
    #: What went missing, because the consequence differs and so must the sentence that reports
    #: it. A stale unit is included by `\protectedInput` and prints the deleted problem; a stale
    #: language is a whole booklet nobody asked for, built for a translation that is gone.
    kind: str = 'unit'          # 'unit' or 'language'

    def __str__(self):
        return f'{self.stage}/{self.rel}'


def _sweep(sources, parents: set, known: set, kind: str) -> list[Orphan]:
    """
    Directories beside `parents` whose names are not in `known` and have no source left.

    The one loop both passes below share. Reads directories and nothing else -- no file is
    opened, nothing is written, and a tree with no `build/` in it simply yields nothing, the way
    `macro-undefined` reports nothing when its sweep has never run.
    """
    found = []
    for stage in STAGES:
        for parent in sorted(parents):
            built = sources.repo_root / stage / sources.module / parent
            if not built.is_dir():
                continue
            for child in sorted(built.iterdir()):
                if not child.is_dir() or child.name.startswith('.'):
                    continue
                rel = parent / child.name
                if str(rel) in known or (sources.module_root / rel).is_dir():
                    continue
                found.append(Orphan(stage, str(rel), child,
                                    sum(1 for f in child.rglob('*') if f.is_file()), kind))
    return found


def unit_orphans(sources) -> list[Orphan]:
    """Stale unit directories: a problem renamed or deleted, its build left behind."""
    units = [Path(unit.path) for unit in sources.unit_list]
    if not units:
        return []                       # no units, so no notion of where a unit belongs

    # Where units live, and which names are theirs. Both come from the sources, which is what
    # keeps this module-agnostic: naboj puts them under `problems/`, seminar under `1/1`, `1/2`
    # and so on, and neither is written down here.
    return _sweep(sources, {unit.parent for unit in units},
                  {str(unit) for unit in units}, 'unit')


def language_orphans(sources) -> list[Orphan]:
    r"""
    Stale language directories: a translation dropped, its `.tex` left behind.

    The same narrow shape as the unit pass -- a named set of children of one known parent -- and
    it is here because the unit pass cannot see it. `languages/` is not a place units live, so
    `build/naboj/phys/29/languages/uk/` is invisible to that sweep however long it sits there.

    **It is self-limiting rather than naboj-specific.** A module with no `languages/` directory
    beside its scope has no notion of a language directory and yields nothing, which is how
    seminar and scholar pass through -- monolingual, one language and not one of several.

    This is the half that lets a deleted translation keep building. The language documents in
    `modules/naboj/module.mk` are pattern rules, so `%` matches any string; a stale `build/`
    language directory supplies everything they ask for, and `make …/languages/uk/booklet.pdf`
    for a volume with no Ukrainian produces a booklet out of files whose sources are gone.
    Volume 29 did exactly that -- a 40-page Ukrainian problems booklet, in a volume that has
    `en`, `es` and `sk`. The `source/naboj/$*/meta.yaml` prerequisite added there is the other
    half: it refuses a cold build, and this finds the warm one.
    """
    languages = sources.module_root / sources.scope / 'languages'
    if not languages.is_dir():
        return []

    parent = Path(sources.scope) / 'languages'
    known = {str(parent / child.name) for child in languages.iterdir() if child.is_dir()}
    return _sweep(sources, {parent}, known, 'language')


def orphans(sources) -> list[Orphan]:
    """Every stale directory for one scope -- units, then languages, `render/` before `build/`."""
    return unit_orphans(sources) + language_orphans(sources)


def remove(orphan: Orphan) -> int:
    """
    Delete one orphan, returning how many files went.

    A plain recursive delete, and the safety is upstream: `orphans` only ever names a directory
    that sits beside units, is not one, and has no source counterpart. Nothing here resolves a
    symlink -- `rglob` lists them and `unlink` removes the link rather than its target -- which
    matters because `source/` holds 84 of them and a careless prune would follow one out of the
    build tree.
    """
    gone = 0
    for path in sorted(orphan.path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if path.is_symlink() or path.is_file():
            path.unlink()
            gone += 1
        elif path.is_dir():
            path.rmdir()
    orphan.path.rmdir()
    return gone
