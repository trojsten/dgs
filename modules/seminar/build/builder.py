import sys

sys.path.append('.')

from core.utilities import builder


class BuilderSeminar(builder.BaseBuilder):
    module = 'seminar'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-c', '--competition', choices=['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
        self.parser.add_argument('-v', '--volume', type=int)
        self.parser.add_argument('-s', '--semester', type=int)
        self.parser.add_argument('-r', '--round', type=int)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester, self.args.round)

    def path(self):
        return (
            '' if self.args.competition is None else self.args.competition,
            '' if self.args.volume is None else f'{self.args.volume:02d}',
            '' if self.args.semester is None else str(self.args.semester),
            '' if self.args.round is None else str(self.args.round),
        )


class BuilderRound(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester, self.args.round)


class BuilderSemester(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester)
