"""
One read of everything a scope contains, so every check works from the same snapshot.

Reading is cheap -- the whole of `source/naboj/phys`, 4704 markdown files and 463 metas, takes
about a fifth of a second -- so there is no laziness here and no cache to invalidate. Reading
through a symlink is safe; nothing in the audit ever writes.
"""
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: Files beside the unit rather than inside a language directory.
LANGUAGE_RE_LEN = 2


@dataclass
class Unit:
    """One problem (or handout, or whatever the module's editable thing is)."""
    path: str                               # relative to the module root, e.g. '28/problems/nevera'
    root: Path                              # absolute
    meta_raw: str | None = None             # None when there is no meta.yaml at all
    meta: dict | None = None                # parsed; None when absent, empty or unparseable
    meta_error: str | None = None
    shared: dict = field(default_factory=dict)      # name -> text, for .md beside the unit
    translated: dict = field(default_factory=dict)  # lang -> {name -> text}
    assets: set = field(default_factory=set)        # every non-markdown file name
    #: name -> what the symlink points at, verbatim. A translation nobody has written yet mirrors
    #: its master this way, so the target names the language it is waiting on.
    links: dict = field(default_factory=dict)

    @property
    def name(self):
        return self.path.rsplit('/', 1)[-1]

    @property
    def languages(self):
        return sorted(self.translated)

    def files(self):
        """Every markdown file, as (language or '', name, text). Language '' means shared."""
        for name, text in sorted(self.shared.items()):
            yield '', name, text
        for lang in sorted(self.translated):
            for name, text in sorted(self.translated[lang].items()):
                yield lang, name, text

    def label(self, lang, name):
        return f"{lang}/{name}" if lang else name


@dataclass
class Sources:
    """A scope, read."""
    module: str
    scope: str                              # e.g. 'phys/28'
    module_root: Path
    units: dict = field(default_factory=dict)   # path -> Unit, in sorted order

    @property
    def unit_list(self):
        return list(self.units.values())

    def fingerprint(self):
        """
        A digest of every source file's size and mtime, so a cached build result can say whether
        the sources have moved since it ran.
        """
        h = hashlib.sha1()
        for unit in self.units.values():
            for f in sorted(unit.root.rglob('*')):
                if f.is_file():
                    st = f.stat()
                    h.update(f"{f}:{st.st_size}:{st.st_mtime_ns}".encode())
        return h.hexdigest()


def _is_language_dir(path: Path):
    return path.is_dir() and len(path.name) == LANGUAGE_RE_LEN and path.name.isalpha()


def read_unit(module_root: Path, unit_path: str) -> Unit:
    root = module_root / unit_path
    unit = Unit(path=unit_path, root=root)

    meta = root / 'meta.yaml'
    if meta.is_file():
        unit.meta_raw = meta.read_text()
        if unit.meta_raw.strip():
            try:
                loaded = yaml.safe_load(unit.meta_raw)
                unit.meta = loaded if isinstance(loaded, dict) else None
                if loaded is not None and not isinstance(loaded, dict):
                    unit.meta_error = f"top level is {type(loaded).__name__}, not a mapping"
            except yaml.YAMLError as e:
                unit.meta_error = str(e).splitlines()[0]

    for child in sorted(root.iterdir()):
        if child.is_symlink():
            unit.links[child.name] = os.readlink(child)
        if child.is_file():
            if child.suffix == '.md':
                unit.shared[child.name] = child.read_text()
            elif child.name != 'meta.yaml':
                unit.assets.add(child.name)
        elif _is_language_dir(child):
            files = {}
            for f in sorted(child.iterdir()):
                if f.is_symlink():
                    unit.links[f"{child.name}/{f.name}"] = os.readlink(f)
                if f.is_file() and f.suffix == '.md':
                    files[f.name] = f.read_text()
                elif f.is_file():
                    unit.assets.add(f"{child.name}/{f.name}")
            unit.translated[child.name] = files
    return unit


def read_scope(module_root: Path, module_name: str, scope: str, unit_paths) -> Sources:
    return Sources(
        module=module_name,
        scope=scope,
        module_root=module_root,
        units={p: read_unit(module_root, p) for p in sorted(unit_paths)},
    )


def link_language(target: str):
    """
    The language a mirrored translation points at, or None if the link goes somewhere else.

    Targets look like `../sk/solution.md`: a translation that has not been written yet mirrors its
    master rather than keeping a stale copy, which is what `27/water-level/cs/solution.md` is.
    """
    parts = [p for p in target.split('/') if p not in ('..', '.')]
    if len(parts) == 2 and len(parts[0]) == 2 and parts[0].isalpha():
        return parts[0]
    return None
