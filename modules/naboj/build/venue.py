import builder
import context


class BuilderNabojVenue(builder.BuilderNaboj):
    target = 'venue'
    subdir = 'venues'

    root_context_class = context.ContextTearoff
    templates = ['barcodes.txt', 'tearoff.tex', 'envelopes.tex']

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-p', '--venue', type=str)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.venue)

    def path(self):
        return (self.args.competition, f'{self.args.volume:02d}', self.subdir, self.args.venue)


BuilderNabojVenue().build()
