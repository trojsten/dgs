"""
A problem's translated words, one file per language.

`<problem>/<lang>/words.yaml` holds `term: text` and nothing else -- the directory is the
language, so no entry repeats it. The renderer reads one of these files, the audit and the editor
read all of them at once, and this module is the only place that knows the name or the shape.

**It used to be a `words:` key in `meta.yaml`**, term -> language -> text. That block had to go
somewhere a translator works, and the two obvious places do not survive contact with the corpus:

- **in the `.md` itself** there is no per-language file to put it in. 84 translations under
  `source/` are symlinks, so `28/john-doe/pl/solution.md` *is* `en/solution.md`, and eight live
  cases need a different word on either side of the link -- `vol` is `gulp` for English and `łyk`
  for Polish. One file cannot hold both. It also duplicates per file: `21/pool-jump`'s `twin` is
  needed by `problem.md` and `solution.md`, and the drift between those two is the defect the key
  was invented to fix.
- **a `<lang>/preamble.md`** fixes both and brings back a mechanism that was deleted, with no
  schema on it.

A directory is never a symlink here -- only files are -- so `es/words.yaml` is a real file even
where `es/solution.md` points at `../en/solution.md`, which is what makes this placement work at
all.

**What it costs is the one view where every language of a term sat together**, which is where
`21/pool-jump`'s mismatched density subscript was found. `rows()` is that view, assembled back
out of the files for the `/audit` page and the editor.
"""
import io
import logging
from pathlib import Path

import yaml
from enschema import Optional as Opt
from enschema import Schema, SchemaError

from core.builder.context.context import UniqueKeyLoader, ValidIdentifier
from core.utilities import colour as c

log = logging.getLogger('dgs')


#: The file a language's words live in, beside that language's prose.
WORDS_FILE = 'words.yaml'

#: Flat, because the directory already says which language this is. Spelling the language inside
#: the file as well would be two places to get it wrong, and the wrong one would be invisible --
#: a `cs:` key inside `sk/words.yaml` reads perfectly and means nothing.
SCHEMA = Schema({Opt(ValidIdentifier): str})

#: A language directory, by the same rule `core/audit/sources.py` uses: two letters, nothing else.
LANGUAGE_NAME_LENGTH = 2


class WordsFileError(Exception):
    """
    A `words.yaml` that does not parse or does not validate, named by path.

    Loud rather than skipped. A words file that fails to load would otherwise behave exactly like
    one that is not there -- every term in it boxed in red and the render failing a long way from
    the cause -- and the two want opposite fixes.
    """
    def __init__(self, path: Path, problem: Exception | str):
        super().__init__(f"{path}: {problem}")
        self.path = path


def is_language_dir(path: Path) -> bool:
    """Whether this is a language directory. Same rule as `core/audit/sources.py`."""
    return path.is_dir() and len(path.name) == LANGUAGE_NAME_LENGTH and path.name.isalpha()


def path_for(root: Path, locale: str) -> Path:
    """
    Where a locale's words live, given the **problem** directory.

    Keyed off the locale rather than off the directory of the file being rendered, and that is not
    a detail: `18/bathmobile/answer.md` sits at the problem root, because an answer in `14`-`18` is
    a value and needs no translated copy, and it is still rendered once per language. A rule of
    "beside the file" would find nothing for it in every language.

    A module with no language directories at all -- seminar and scholar are monolingual -- gets
    `<root>/words.yaml`. Nothing uses that today; it is defined so the fallback is not a surprise.
    """
    if not locale or not (root / locale).is_dir():
        return root / WORDS_FILE
    return root / locale / WORDS_FILE


def load(root: Path, locale: str) -> dict[str, str]:
    """
    One language's words, or `{}` where the file is absent.

    Absent is not an error, and the caller must not treat it as one: a problem with no translated
    words has no file in any language, and a language that needs none has none of its own. What
    makes a word *required* is a template asking for it, which is `LocalisedWords`' business --
    it boxes the miss in red, records it and lets the render reach the end before failing.
    """
    where = path_for(root, locale)
    if not where.is_file():
        return {}
    return load_string(where.read_text(), where=where)


def load_string(text: str, *, where: Path | str = '<words.yaml>') -> dict[str, str]:
    """
    The same from text that is not on disk, which is what the editor holds while it is being typed.

    `where` is passed through to PyYAML's stream name so a duplicate term names its own file; see
    `Context.load_string`, which does this for the same reason.
    """
    stream = io.StringIO(text)
    stream.name = str(where)
    try:
        loaded = yaml.load(stream, Loader=UniqueKeyLoader)
    except yaml.YAMLError as e:
        raise WordsFileError(Path(str(where)), str(e).splitlines()[0]) from e
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise WordsFileError(Path(str(where)),
                             f"top level is {type(loaded).__name__}, not a mapping")
    try:
        SCHEMA.validate(loaded)
    except SchemaError as e:
        raise WordsFileError(Path(str(where)), str(e).splitlines()[0]) from e
    return loaded


def languages(root: Path) -> list[str]:
    """Every language of this problem that declares words, sorted."""
    return sorted(child.name for child in root.iterdir()
                  if is_language_dir(child) and (child / WORDS_FILE).is_file())


def rows(root: Path) -> dict[str, dict[str, str]]:
    """
    Every term of this problem against every language that spells it: `term -> locale -> text`.

    This is the view the single `words:` block used to give for free, and the reason to rebuild it
    rather than let it go. `21/pool-jump` wrote `\\rho_s` in Slovak and Czech and `\\rho_t` in
    English and Hungarian while the shared equation printed `\\rho_s`, so the English booklet
    introduced one symbol and solved with another. Four values on one line is what makes that
    visible; four files do not.

    Terms come back in the order the languages declare them, first file first, so a problem whose
    languages agree on an order keeps it. A term only one language has is still a row -- that is
    usually the gap, not a term belonging to one reader.
    """
    return invert({locale: load(root, locale) for locale in languages(root)})


def invert(per_language: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """
    `locale -> term -> text` the other way up, which is the shape the row view wants.

    Separate from `rows()` because the audit has already read every file -- `Unit.words` is the
    same mapping -- and reading them a second time to turn them round would be the one thing
    `core/audit/sources.py` exists to avoid.
    """
    out: dict[str, dict[str, str]] = {}
    for locale in sorted(per_language):
        for term, text in (per_language[locale] or {}).items():
            out.setdefault(term, {})[locale] = text
    return out
