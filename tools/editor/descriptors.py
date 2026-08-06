"""
Discovery of editable units, driven entirely by `modules/<module>/editor.yaml`.

The editor knows three things about a module -- where its units live, what files they hold, and
which document previews one -- and it learns all three from that file. Nothing here mentions
Náboj, seminar or scholar by name, so a fourth module needs a descriptor and no code.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DESCRIPTOR = "editor.yaml"

# Not prose, but part of the document all the same: a gnuplot script is Jinja-rendered like
# everything else and becomes a figure, and the .dat tables it plots are its prerequisites.
AUX_EXTENSIONS = (".gp", ".dat")
RENDERABLE_AUX_EXTENSIONS = (".gp",)


@dataclass(frozen=True)
class UnitKind:
    """One `units:` entry: a shape of directory, and what to do with it."""
    glob: str
    levels: tuple = ()           # what each path segment is: competition, volume, problem, ...
    targets: tuple = ()          # every file the unit may hold, in the order the tabs appear
    translated: tuple = ()       # the subset living inside <language>/ rather than beside it
    render: str = ""
    preview: str = ""

    @property
    def fixed_levels(self):
        """
        Depths the glob pins to a literal, like Náboj's `problems/`. Those are not a choice and
        the picker leaves them out -- unlike a level that merely has one value at the moment,
        which is what a seminar competition looks like when only FKS is checked out.
        """
        return tuple(i for i, segment in enumerate(self.glob.split("/"))
                     if not any(c in segment for c in "*?["))

    @property
    def all_targets(self):
        return tuple(self.targets)

    def is_translated(self, target):
        return target in self.translated


@dataclass(frozen=True)
class Module:
    name: str
    label: str
    languages: bool
    kinds: tuple
    root: Path

    def kind_for(self, unit: str):
        """Which `units:` entry this unit matches, or None if it is not a unit at all."""
        return discover_units(self).get(unit)


def load_modules(repo_root: Path):
    """Every module that ships a descriptor and has a populated source tree, by name."""
    modules = {}
    for descriptor in sorted(repo_root.glob(f"modules/*/{DESCRIPTOR}")):
        name = descriptor.parent.name
        root = repo_root / "source" / name
        if not root.is_dir():
            continue
        spec = yaml.safe_load(descriptor.read_text()) or {}
        modules[name] = Module(
            name=name,
            label=spec.get("label", name),
            languages=bool(spec.get("languages", False)),
            kinds=tuple(
                UnitKind(
                    glob=entry["glob"],
                    levels=tuple(entry.get("levels") or ()),
                    targets=tuple(entry.get("targets") or ()),
                    translated=tuple(entry.get("translated") or ()),
                    render=entry.get("render", ""),
                    preview=entry.get("preview", ""),
                )
                for entry in spec.get("units") or []
            ),
            root=root,
        )
    return modules


def _holds_something(path: Path, kind: UnitKind, languages: bool) -> bool:
    """
    A directory of the right shape is not yet a unit -- `FKS/.git/logs/refs/heads` has the shape
    of a seminar problem. Require a meta.yaml or at least one of the files the kind expects.
    Not both: an unconverted problem has no meta.yaml, and a brand new one has no text yet.
    """
    if (path / "meta.yaml").is_file():
        return True
    names = [f"{target}.md" for target in kind.all_targets]
    if any((path / name).is_file() for name in names):
        return True
    if languages:
        return any((child / name).is_file()
                   for child in path.iterdir() if child.is_dir()
                   for name in names)
    return False


def discover_units(module: Module):
    """
    Every unit of every kind, as paths relative to the module's source root, mapped to its kind.

    Directories, not `meta.yaml` files: a unit that has not been converted yet has no meta.yaml,
    and those are exactly the ones somebody needs to open in order to write one. Longest glob
    first, so scholar's four-segment handout does not claim the five-segment problems inside it.
    """
    units = {}
    for kind in sorted(module.kinds, key=lambda k: -len(k.glob.split("/"))):
        for path in sorted(module.root.glob(kind.glob)):
            unit = path.relative_to(module.root).as_posix()
            # Dotted directories are infrastructure -- `.git`, `.static`, `.template` -- and
            # `FKS/.git/logs/refs/heads` matches a five-segment glob just as well as a problem.
            if any(part.startswith(".") for part in unit.split("/")):
                continue
            if path.is_dir() and _holds_something(path, kind, module.languages):
                units.setdefault(unit, kind)
    return units
