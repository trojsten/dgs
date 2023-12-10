import abc
import logging
import pprint

from enschema import Schema, SchemaError, And, Or, Regex
from pathlib import Path

log = logging.getLogger('dgs')

Link = 'link'
File = 'file'
FileOrLink = Or(File, Link)
String = And(str, len)
CommitHash = Regex(r'[a-f0-9]+')


class FileSystemValidator(metaclass=abc.ABCMeta):
    IGNORED = ['.git']

    _schema: Schema = None

    @property
    def schema(self) -> Schema:
        return self._schema

    def __init__(self, root):
        self.root = Path(root)
        self.tree = self.scan(self.root)

    def scan(self, path) -> str | dict | None:
        if path.name in self.IGNORED:
            return None
        if path.is_dir():
            return {
                child.name: self.scan(Path(child)) for child in path.iterdir() if child.name[0] not in self.IGNORED
            }
        else:
            if path.is_symlink():
                return Link
            elif path.is_file():
                return File

    def validate(self) -> None:
        """
        Validate the tree, re-raising the corresponding SchemaError if anything is out of order
        """
        try:
            self.schema.validate(self.tree)
            self.perform_extra_checks()
        except SchemaError as e:
            log.error(f"Could not validate file system tree")
            pprint.pprint(self.tree)
            log.error(f"against schema\n{self.schema}")
            raise e

    def perform_extra_checks(self) -> None:
        """
        Extra checks that are impossible or cumbersome to implement with schema.
        Runs *after* schema validation. By default, this is a no-op.
        """
        pass
