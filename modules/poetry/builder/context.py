import os
import sys
from pathlib import Path

sys.path.append('.')

from core.utilities import context


class ContextPoetry(context.Context):
    def node_path(self, author, title=None):
        return Path(
            author,
            '' if title is None else title,
        )


class ContextAuthor(ContextPoetry):
    def __init__(self, root, author, title=None):
        super().__init__()
        self.load_meta(root, author)


class ContextPoem(ContextPoetry):
    def __init__(self, author, title):
        self.load_meta(root, author, title)
