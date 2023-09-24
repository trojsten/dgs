import sys

sys.path.append('.')

from core.builder import builder


class BuilderSeminar(builder.BaseBuilder):
    module = 'seminar'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-c', '--competition', choices=['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX', 'FKS-old', 'testing'])
        self.parser.add_argument('-v', '--volume', type=int)
        self.parser.add_argument('-s', '--semester', type=int)
        self.parser.add_argument('-r', '--round', type=int)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester, self.args.round)

    def path(self):
        return (
            str(builder.empty_if_none(self.args.competition)),
            str(builder.empty_if_none(self.args.volume)),
            str(builder.empty_if_none(self.args.semester)),
            str(builder.empty_if_none(self.args.round)),
        )


class BuilderVolume(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume)


class BuilderSemester(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester)


class BuilderRound(BuilderSeminar):
    def id(self):
        return (self.args.competition, self.args.volume, self.args.semester, self.args.round)
