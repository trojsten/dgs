import sys
import context

sys.path.append('.')

from core.utilities import builder


class BuilderPoetry(builder.BaseBuilder):
    module = 'poetry'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-a', '--author', type=str)
        self.parser.add_argument('-t', '--title', type=str)


