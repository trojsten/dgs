import abc
import sys

sys.path.append('.')

from core.builder import builder


class BuilderScholarBase(builder.BaseBuilder, metaclass=abc.ABCMeta):
    module = 'scholar'


class BuilderScholar(BuilderScholarBase):
    _subdir = None

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('course', type=str)
        self.parser.add_argument('year', type=int)
        self.parser.add_argument('issue', type=int)

    def id(self):
        return self.args.course, self.args.year, self.args.issue

    def path(self):
        return self.args.course, f'{self.args.year:04d}', self._subdir, f'{self.args.issue:02d}'


class BuilderCourseBase(BuilderScholarBase):
    def path(self):
        return self.id()
