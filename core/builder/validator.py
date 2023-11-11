import abc
import pprint
from schema import Schema
from pathlib import Path


class FileSystemValidator(metaclass=abc.ABCMeta):
    @property
    def schema(self) -> Schema:
       pass

    def __init__(self, root):
        self.root = Path(root)
        self.tree = self.scan(self.root)

    def scan(self, path):
        if path.name[0] == '.':
            return None
        if path.is_dir():
            return {
                child.name: self.scan(Path(child)) for child in path.iterdir() if child.name[0] != '.'
            }
        else:
            return open(path, 'r')

    def validate(self):
        self.schema.validate(self.tree)
