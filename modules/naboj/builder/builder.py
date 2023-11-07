import sys

sys.path.append('.')

from core.builder import builder
from contexts import ContextNaboj


class BuilderNaboj(builder.BaseBuilder):
    class Meta:
        abstract = True

    module = 'naboj'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('competition', choices=['phys', 'math', 'chem', 'junior', 'test'])
        self.parser.add_argument('volume', type=int)
