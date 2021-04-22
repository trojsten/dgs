import sys

sys.path.append('.')

from core.utilities import builder


def empty_if_none(what):
    return '' if what is None else what


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
            empty_if_none(self.args.competition),
            empty_if_none(self.args.volume),
            empty_if_none(self.args.semester),
            empty_if_none(self.args.round),
        )


class BuilderRound(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester, self.args.round)


class BuilderSemester(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester)
