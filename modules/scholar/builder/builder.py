import abc
from pathlib import Path

from core.builder.builder import BaseBuilder
from core.builder.jinja import StaticRenderer


class BuilderScholarBase(BaseBuilder, metaclass=abc.ABCMeta):
    module = 'scholar'


class BuilderScholar(BuilderScholarBase):
    _subdir = None

    _renderer_class = StaticRenderer

    def __init__(self):
        super().__init__()

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('course', type=str)
        self.parser.add_argument('year', type=int)
        self.parser.add_argument('issue', type=int)

    def ident(self):
        return self.args.course, self.args.year, self.args.issue

    def path(self):
        return self.args.course, f'{self.args.year:04d}', self._subdir, f'{self.args.issue:02d}'


class BuilderCourseBase(BuilderScholarBase, metaclass=abc.ABCMeta):
    def path(self):
        return self.ident()
