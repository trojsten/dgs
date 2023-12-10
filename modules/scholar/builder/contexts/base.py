from abc import ABCMeta
from pathlib import Path

from core.builder import context


class ContextScholar(context.FileSystemContext, metaclass=ABCMeta):
    _target = None
    _subdir = None

    @staticmethod
    def as_tuple(course=None, year=None, kind=None, issue=None, *deeper):
        result = []
        if course is not None:
            assert isinstance(course, str)
            result.append(course)
            if year is not None:
                assert isinstance(year, int)
                result.append(f'{year:04d}')
                if issue is not None:
                    assert kind is not None, (course, year, kind, issue, *deeper)
                    assert isinstance(issue, int)
                    result.append(kind)
                    result.append(f'{issue:02d}')
        return tuple(result)

    def ident(self, course=None, year=None, issue=None, *deeper):
        return self.as_tuple(course, year, self._target, issue, *deeper)

    def node_path(self, course=None, year=None, issue=None, *deeper):
        return Path(self.root, *self.as_tuple(course, year, self._subdir, issue), *deeper)
