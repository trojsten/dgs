import logging
from pathlib import Path

from core.utilities import colour as c

log = logging.getLogger('dgs')


class Crawler():
    def __init__(self, root):
        self.step = 4
        self.root = root

    @staticmethod
    def is_node(path: Path) -> bool:
        return path.is_dir() and path.name[0] != '.' and Path(path, 'meta.yaml').is_file()

    @staticmethod
    def is_leaf(path: Path) -> bool:
        return path.is_file() and path.basename[0] != '.'

    def print_path(self, path=None, offset=0):
        if path is None:
            path = Path(self.root)

        if self.is_node(path):
            colour = c.node
        else:
            if path.is_dir():
                colour = c.notnode
            else:
                colour = c.meta if path.name == 'meta.yaml' else c.leaf

        print(f"{' ' * offset * self.step}{colour(path.name)}")

        if self.is_node(path):
            for child in sorted(path.iterdir()):
                self.print_path(child, offset + 1)

    def children(self):
        return [child.name for child in sorted(self.root.iterdir()) if self.is_node(child)]

    def subdirs(self):
        """ DeGeŠ should ignore all directories starting with '.' """
        return [child.name for child in sorted(self.root.iterdir()) if child.is_dir() and not child.name.startswith('.')]

    def __str__(self):
        return f"Crawler at {self.root}"
