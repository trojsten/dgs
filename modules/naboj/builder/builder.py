import abc
import sys

sys.path.append('.')

from core.builder import builder


class BuilderNaboj(builder.BaseBuilder, metaclass=abc.ABCMeta):
    module = 'naboj'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('competition', choices=['phys', 'math', 'chem', 'junior', 'test'])
        self.parser.add_argument('volume', type=int)
