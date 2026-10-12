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

**A unit directory, and nothing coarser.** `build/` is full of directories with no source
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
    """One built unit directory with no source left."""
    stage: str                  # 'render' or 'build'
    rel: str                    # path below the stage root, e.g. 'phys/pool/problems/old-name'
    path: Path                  # absolute
    files: int                  # how much is in there, for a report that says what it would cost

    def __str__(self):
        return f'{self.stage}/{self.rel}'


def orphans(sources) -> list[Orphan]:
    """
    Every stale unit directory for one scope, `render/` before `build/`.

    Reads directories and nothing else -- no file is opened, nothing is written, and a tree with
    no `build/` in it simply yields nothing, the way `macro-undefined` reports nothing when its
    sweep has never run.
    """
    units = [Path(unit.path) for unit in sources.unit_list]
    if not units:
        return []                       # no units, so no notion of where a unit belongs

    # Where units live, and which names are theirs. Both come from the sources, which is what
    # keeps this module-agnostic: naboj puts them under `problems/`, seminar under `1/1`, `1/2`
    # and so on, and neither is written down here.
    parents = {unit.parent for unit in units}
    known = {str(unit) for unit in units}

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
                                    sum(1 for f in child.rglob('*') if f.is_file())))
    return found


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
