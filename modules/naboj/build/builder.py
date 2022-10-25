import sys

sys.path.append('.')

from core.utilities import builder


class BuilderNaboj(builder.BaseBuilder):
    module = 'naboj'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-c', '--competition', choices=['FKS', 'KMS', 'junior', 'chem'])
        self.parser.add_argument('-v', '--volume', type=int)
