import builder
from modules.naboj.builder.contexts import BuildableContextVenue


class BuilderNabojVenue(builder.BuilderNaboj):
    target = 'venue'
    subdir = 'venues'

    root_context_class = BuildableContextVenue
    templates = [
        'barcodes.jtt',
        'tearoff.jtt',
        'envelopes.jtt',
        'instructions.jtt',
        'answers-modulo.jtt',
    ]
    i18n_templates = ['instructions-inner.jtt', 'evaluators.jtt']

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('venue', type=str)

    def id(self):
        return self.args.competition, self.args.volume, self.args.venue

    def path(self):
        return self.args.competition, f'{self.args.volume:02d}', self.subdir, self.args.venue


BuilderNabojVenue().build()
