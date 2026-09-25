"""
Discovery of editable units, driven entirely by `modules/<module>/editor.yaml`.

The editor knows three things about a module -- where its units live, what files they hold, and
which document previews one -- and it learns all three from that file. Nothing here mentions
Náboj, seminar or scholar by name, so a fourth module needs a descriptor and no code.
"""
from dataclasses import dataclass
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
    #: Only for a module whose `.tex` rule is not the usual one; normally empty and derived.
    tex_override: str = ""

    @property
    def tex(self):
        """
        The make target that converts this file to TeX.

        Derived from `render` rather than written out per module, because the relation is the
        build system's own: every `.tex` rule in every `module.mk` reads
        `build/<module>/%/<name>.tex: render/<module>/%/<name>.md`. Deriving it cannot drift,
        whereas six hand-written keys across three descriptors -- scholar alone has four unit
        kinds -- can. `tex_override` exists for a module that ever stops following the rule.
        """
        if self.tex_override:
            return self.tex_override
        if not self.render.startswith("render/") or not self.render.endswith(".md"):
            return ""
        return "build/" + self.render[len("render/"):-len(".md")] + ".tex"

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
    #: The level the audit page aggregates at -- a volume for Náboj and seminar, a year for
    #: scholar. Named rather than numbered so a module says what it means; the depth is derived.
    scope: str = ''
    #: Whether the audit page covers this module. Off unless a descriptor asks for it: the checks
    #: and the four verdicts encode Náboj's conventions, and seminar and scholar do not share
    #: them -- auditing those against Náboj's rules would report differences as defects. When
    #: either grows conventions worth checking it will want its own checks, not these.
    audit: bool = False

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
                    tex_override=entry.get("tex", ""),
                )
                for entry in spec.get("units") or []
            ),
            root=root,
            scope=spec.get("scope", ""),
            audit=bool(spec.get("audit", False)),
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


def scope_depth(module: Module) -> int:
    """
    How many path segments a scope is: the position of the module's `scope` level, plus one.

    Defaults to two, which is what all three current modules want -- `phys/28`, `FKS/41`,
    `TA1/2025` -- so a module only needs the key if its levels are arranged differently.
    """
    if module.scope:
        for kind in module.kinds:
            if module.scope in kind.levels:
                return kind.levels.index(module.scope) + 1
    return 2


def audited_modules(modules):
    """The modules the audit page covers, in label order."""
    return [m for m in sorted(modules.values(), key=lambda m: m.label) if m.audit]


def discover_scopes(module: Module):
    """
    Every scope in the module, mapped to the units it contains.

    A scope with no units is not a scope: `source/naboj/phys/03` has a volume directory and no
    problems in it, and offering it would be offering an empty page.
    """
    depth = scope_depth(module)
    scopes = {}
    for unit in sorted(discover_units(module)):
        segments = unit.split("/")
        if len(segments) < depth:
            continue
        scopes.setdefault("/".join(segments[:depth]), []).append(unit)
    return scopes


def declared_sources(repo_root: Path):
    """
    Which repositories a module's content lives in, from its own descriptor.

    This used to read `.gitmodules`. It no longer can, and should not have: nothing under
    `source/` was ever a submodule of this repository -- `source/` is gitignored and the index
    holds no gitlinks for it -- so those entries were a fiction that made `git submodule` look
    like the way to populate the tree. The descriptor is the honest home: it is already where a
    module says what it contains, and this is where its content comes from.
    """
    declared = {}
    for descriptor in sorted(repo_root.glob(f"modules/*/{DESCRIPTOR}")):
        spec = yaml.safe_load(descriptor.read_text()) or {}
        entries = [
            {"path": entry.get("path", ""), "url": entry.get("url", "")}
            for entry in spec.get("sources") or []
            if entry.get("path")
        ]
        if entries:
            declared[descriptor.parent.name] = entries
    return declared


def describe_source(repo_root: Path):
    """
    Why the picker is empty, in enough detail to act on.

    `load_modules` skips a module whose `source/<name>/` is absent, which is right -- but on a
    fresh clone that silently means *every* module, and the editor opens showing nothing at all.
    This is what the page says instead.
    """
    declared = declared_sources(repo_root)
    loaded = load_modules(repo_root)
    modules = []
    for descriptor in sorted(repo_root.glob(f"modules/*/{DESCRIPTOR}")):
        name = descriptor.parent.name
        spec = yaml.safe_load(descriptor.read_text()) or {}
        root = repo_root / "source" / name
        present = root.is_dir()
        module = loaded.get(name)
        units = len(discover_units(module)) if module else 0
        modules.append({
            "name": name,
            "label": spec.get("label", name),
            "present": present,
            "units": units,
            "expected": declared.get(name, []),
        })
    return {
        "empty": not any(m["units"] for m in modules),
        "modules": modules,
        # Said once, here, because it is the thing that costs a newcomer an hour.
        # Deliberately not a git command: nothing under `source/` is a submodule of this
        # repository, so there is nothing for `git submodule` to do. Clone them in.
        "note": ("`source/` is gitignored and holds independent repositories, not submodules. "
                 "Clone the ones you need into the paths above; one module is enough to work."),
    }
