import logging
from pathlib import Path

from core.utils import colour as c

logger = logging.getLogger('root')


class Crawler():
    def __init__(self, root):
        self.step = 4
        self.root = root

    def is_node(self, path):
        return (path.is_dir() and path.name != '.' and Path(path, 'meta.yaml').is_file())

    @staticmethod
    def is_leaf(path):
        return path.is_file()

    def print_path(self, path=None, offset=0):
        if path == None:
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
        return [child.name for child in sorted(self.root.iterdir()) if child.is_dir()]

    def __str__(self):
        return f"Crawler at {self.root}"
