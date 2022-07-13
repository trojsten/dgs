import sys

sys.path.append('.')

from core.utilities import builder


class BuilderScholar(builder.BaseBuilder):
    module = 'scholar'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('course', type=str)
        self.parser.add_argument('year', type=int)
        self.parser.add_argument('issue', type=int)

    def id(self):
        return (self.args.course, self.args.year, self.args.issue)

    def path(self):
        return (self.args.course, f'{self.args.year:04d}', self.subdir, f'{self.args.issue:02d}')


class BuilderSingle(builder.BaseBuilder):
    module = 'scholar'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('course', type=str, choices=['FKS'])
        self.parser.add_argument('lecture', type=str)

    def id(self):
        return (self.args.course, self.args.lecture)

    def path(self):
        return self.id()
