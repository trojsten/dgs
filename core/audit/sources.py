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

#: The two rule families in `modules/naboj/module.mk`: `NABOJ_TRANSLATABLE` puts a file inside
#: `<language>/`, `NABOJ_NONTRANSLATABLE` beside the unit. These are the fallback for a caller that
#: does not say -- `tools/editor` passes the module descriptor's lists, which
#: `core/tests/test_audit.py` pins to module.mk so the two cannot drift apart.
TRANSLATED_FILES = ('problem.md', 'problem-extra.md', 'solution.md', 'answer-extra.md')
SHARED_FILES = ('answer.md', 'answer-also.md', 'answer-interval.md')


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
    #: Where this unit sits in the scope meta's `problems:` list, or None when the list does not
    #: name it. The list is what the builder iterates (`ContextVolume`, hierarchy.py:129), so a
    #: unit it omits is a directory that never reaches a PDF.
    order: int | None = None

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

    def real_label(self, lang, name):
        """
        The label of the file this one really is. `27/water-level/cs/solution.md` mirrors `sk`, so
        both point at one set of bytes -- counting them as two copies of an equation overstates the
        duplication and, where a file is reached only through links, invents it.
        """
        target = self.links.get(self.label(lang, name))
        if target is not None:
            mirrored = link_language(target)
            if mirrored is not None:
                return self.label(mirrored, name)
        return self.label(lang, name)


@dataclass
class Sources:
    """A scope, read."""
    module: str
    scope: str                              # e.g. 'phys/28'
    module_root: Path
    units: dict = field(default_factory=dict)   # path -> Unit, in the scope meta's order
    #: the scope's own meta.yaml -- the volume's, not a problem's -- or None if it has none
    scope_meta: dict | None = None
    #: what a unit may hold, from the module's build rules rather than from what happens to be on
    #: disk: a file the rules define and no problem has is a column of blanks worth seeing
    translated_files: tuple = TRANSLATED_FILES
    shared_files: tuple = SHARED_FILES

    def present_translated(self):
        """Translated files any problem in this scope actually has, in the rules' order."""
        found = {name for u in self.units.values() for f in u.translated.values() for name in f}
        found |= {n.split('/', 1)[1] for u in self.units.values() for n in u.links if '/' in n}
        return tuple(n for n in self.translated_files if n in found)

    def present_shared(self):
        """Shared files any problem in this scope actually has, in the rules' order."""
        found = {name for u in self.units.values() for name in u.shared}
        return tuple(n for n in self.shared_files if n in found)

    @property
    def unit_list(self):
        return list(self.units.values())

    @property
    def listed_order(self):
        """The ids the scope meta names, in its order. Empty when there is no list to follow."""
        if not isinstance(self.scope_meta, dict):
            return []
        listed = self.scope_meta.get('problems')
        return [str(p) for p in listed] if isinstance(listed, list) else []

    @property
    def unlisted(self):
        """Units the scope meta does not name, so the build never reaches them."""
        return [u for u in self.units.values() if u.order is None]

    @property
    def missing_from_disk(self):
        """Ids the scope meta names that have no directory."""
        present = {u.name for u in self.units.values()}
        return [p for p in self.listed_order if p not in present]

    def fingerprint(self):
        """
        A digest of every source file's size and mtime, so a cached build result can say whether
        the sources have moved since it ran.
        """
        h = hashlib.sha1()
        # sorted by path, not in `units` order: the order now follows the scope meta, and a digest
        # that moved when the meta was reordered would call every cached build stale for nothing
        for unit in sorted(self.units.values(), key=lambda u: u.path):
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


def read_scope(module_root: Path, module_name: str, scope: str, unit_paths,
               translated_files=TRANSLATED_FILES, shared_files=SHARED_FILES) -> Sources:
    """
    Read a scope, ordered the way the competition is: the scope meta's `problems:` list is the
    running order, easiest first, and it is what the builder iterates. Alphabetical order says
    nothing about a volume, so it is not the default -- but a unit the list does not name still has
    to appear, or the audit would hide exactly the problem worth seeing. Those go last, sorted.
    """
    scope_meta = None
    meta_file = module_root / scope / 'meta.yaml'
    if meta_file.is_file():
        try:
            loaded = yaml.safe_load(meta_file.read_text())
            scope_meta = loaded if isinstance(loaded, dict) else None
        except yaml.YAMLError:
            scope_meta = None

    units = {p: read_unit(module_root, p) for p in sorted(unit_paths)}

    rank = {}
    if isinstance(scope_meta, dict) and isinstance(scope_meta.get('problems'), list):
        for i, name in enumerate(scope_meta['problems']):
            rank.setdefault(str(name), i)
    for unit in units.values():
        unit.order = rank.get(unit.name)

    ordered = sorted(units.values(),
                     key=lambda u: (u.order is None, u.order if u.order is not None else 0, u.path))
    return Sources(
        module=module_name,
        scope=scope,
        module_root=module_root,
        units={u.path: u for u in ordered},
        scope_meta=scope_meta,
        translated_files=tuple(translated_files),
        shared_files=tuple(shared_files),
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
