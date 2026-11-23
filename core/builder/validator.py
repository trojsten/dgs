import abc
import logging
import pprint
from pathlib import Path

import functools
import regex as re
from enschema import And, Or, Regex, Schema, SchemaError

log = logging.getLogger('dgs')

Link = 'link'
File = 'file'
FileOrLink = Or(File, Link)
String = And(str, len)
CommitHash = Regex(r'[a-f0-9]+')


class FileSystemValidator(metaclass=abc.ABCMeta):
    # Paths to ignore within the file structure.
    # Currently, it is a list of strings, but might be converted to regexes later.
    IGNORED: [re.Pattern] = [r'\.git']

    _schema: Schema = None

    @property
    def schema(self) -> Schema:
        return self._schema

    def __init__(self, root):
        self.root = Path(root)
        self.tree = self.scan(self.root)

    #: Compiled once **per pattern set**, not once per class hierarchy. The expressions used to
    #: be rebuilt on every path in the tree -- a fresh `re.compile` per directory entry of every
    #: volume -- and the obvious fix, caching onto `cls`, is worse in a quiet way: the first
    #: subclass to ask writes the attribute, and MRO lookup then hands *its* patterns to every
    #: other subclass. One validator exists today, so it would have been a trap rather than a
    #: bug; keyed on the tuple it compiles, it cannot be either.
    @staticmethod
    @functools.cache
    def _compiled(patterns: tuple) -> tuple:
        return tuple(re.compile(pattern) for pattern in patterns)

    @classmethod
    def _ignored(cls, name: str) -> bool:
        return any(pattern.match(name) for pattern in cls._compiled(tuple(cls.IGNORED)))

    def scan(self, path) -> str | dict | None:
        """
        The tree as a mapping, with the ignored entries **left out** rather than nulled.

        Two things were wrong here and they hid each other. The directory comprehension filtered
        on `child.name[0] not in self.IGNORED` -- one *character* against a list holding the
        four-character string `\\.git` -- so it was always true and had never excluded anything.
        What did the excluding was the `match` above, which returns `None`; and a `None` is still
        a key, so `.git` arrived in the validated tree as an entry every schema then had to
        tolerate. Skipping is what was meant, and it is what lets a schema be exact.
        """
        if self._ignored(path.name):
            return None
        if path.is_dir():
            return {
                child.name: scanned
                for child in path.iterdir()
                if not self._ignored(child.name)
                and (scanned := self.scan(Path(child))) is not None
            }
        else:
            if path.is_symlink():
                return Link
            elif path.is_file():
                return File
            else:
                return None

    def validate(self) -> None:
        """
        Validate the tree, re-raising the corresponding SchemaError if anything is amiss
        """
        try:
            self.schema.validate(self.tree)
            self.perform_extra_checks()
        except SchemaError:
            log.error("Could not validate file system tree")
            pprint.pprint(self.tree)
            log.error(f"against schema\n{self.schema}")
            raise

    def perform_extra_checks(self) -> None:
        """
        Extra checks that are impossible or cumbersome to implement with schema.
        Runs *after* schema validation. By default, this is a no-op.
        """
