from abc import ABCMeta
from pathlib import Path

from core.builder import context


class ContextScholar(context.FileSystemContext, metaclass=ABCMeta):
    target = None
    subdir = None

    def as_tuple(self, course=None, year=None, kind=None, issue=None, *deeper):
        print(self.__class__.__name__, "Producing tuple from", (course, year, kind, issue, *deeper))
        result = []
        if course is not None:
            result.append(course)
            if year is not None:
                result.append(f'{year:04d}')
                if self.target is not None:
                    result.append(kind)
                    if issue is not None:
                        result.append(f'{issue:02d}')
        return tuple(result)

    def ident(self, course=None, year=None, issue=None, *deeper):
        return self.as_tuple(course, year, self.target, issue, *deeper)

    def node_path(self, course=None, year=None, target_type=None, issue=None, *deeper):
        return Path(self.root, *self.as_tuple(course, year, self.subdir, issue), *deeper)


