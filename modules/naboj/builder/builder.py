import sys

sys.path.append('.')

from core.builder import builder


class BuilderNaboj(builder.BaseBuilder):
    class Meta:
        abstract = True

    module = 'naboj'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-c', '--competition', choices=['phys', 'math', 'chem', 'junior'])
        self.parser.add_argument('-v', '--volume', type=int)
