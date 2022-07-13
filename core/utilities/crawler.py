from pathlib import Path

from core.utilities import colour as c


class Crawler():
    def __init__(self, root):
        self.step = 4
        self.root = root

    @staticmethod
    def is_node(path):
        return (path.is_dir() and path.name != '.')

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

