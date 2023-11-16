import abc
from schema import Schema
from pathlib import Path


class FileSystemValidator(metaclass=abc.ABCMeta):
    IGNORED = ['.git']
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
            return open(path, 'r')

    def validate(self) -> None:
        self.schema.validate(self.tree)
        self.perform_extra_checks()

    def perform_extra_checks(self) -> None:
        """
        Extra checks that are impossible or cumbersome to implement with schema.
        Runs *after* schema validation.
        """