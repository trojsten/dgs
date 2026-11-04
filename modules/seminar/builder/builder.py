from core.builder import builder


class BuilderSeminar(builder.BaseBuilder):
    module = 'seminar'

    def add_arguments(self):
        super().add_arguments()
        # A hand-written list of what `source/seminar/` might hold, which is a second copy of
        # what `modules/seminar/editor.yaml` lists under `sources:` and drifts from it -- three
        # of these have never been cloned by anybody. It stays a list only because argparse
        # wants the choices before `launch` has been parsed; `typst` is the Typst-flavoured
        # scratch repository.
        self.parser.add_argument('-c', '--competition',
                                 choices=['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX', 'FKS-old',
                                          'test', 'typst'])
        self.parser.add_argument('-v', '--volume', type=int)
        self.parser.add_argument('-s', '--semester', type=int)
        self.parser.add_argument('-r', '--round', type=int)

    def ident(self):
        return self.args.competition, self.args.volume, self.args.semester, self.args.round

    def path(self):
        return (
            str(builder.empty_if_none(self.args.competition)),
            str(builder.empty_if_none(self.args.volume)),
            str(builder.empty_if_none(self.args.semester)),
            str(builder.empty_if_none(self.args.round)),
        )
