import abc
import logging
import pprint

from enschema import Schema, SchemaError
from pathlib import Path

log = logging.getLogger('dgs')


class FileSystemValidator(metaclass=abc.ABCMeta):
    IGNORED = ['.git']
    Link = 'link'
    File = 'file'
    _schema: Schema | None = None

    @property
    def schema(self) -> Schema:
        return self._schema

    def __init__(self, root):
        self.root = Path(root)
        self.tree = self.scan(self.root)

    def scan(self, path):
        if path.name in self.IGNORED:
            return None
        if path.is_dir():
            return {
                child.name: self.scan(Path(child)) for child in path.iterdir() if child.name[0] not in self.IGNORED
            }
        else:
            if path.is_symlink():
                return FileSystemValidator.Link
            elif path.is_file():
                return FileSystemValidator.File

    def validate(self) -> None:
        try:
            self.schema.validate(self.tree)
            self.perform_extra_checks()
        except SchemaError as e:
            log.error(f"Could not validate file system tree")
            pprint.pprint(self.tree)
            log.error(f"against schema\n\n{self.schema}\n")
            raise e

    def perform_extra_checks(self) -> None:
        """
        Extra checks that are impossible or cumbersome to implement with schema.
        Runs *after* schema validation.
        """
        pass
