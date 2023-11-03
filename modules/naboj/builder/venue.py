from pathlib import Path

import builder
import core.builder.jinja as jinja
from modules.naboj.builder.contexts import BuildableContextVenue


class BuilderNabojVenue(builder.BuilderNaboj):
    target = 'venue'
    subdir = 'venues'

    root_context_class = BuildableContextVenue
    templates = [
        'barcodes.txt',
        'tearoff.tex',
        'envelopes.tex',
        'instructions.tex',
        'answers-modulo.tex'
    ]

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('venue', type=str)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.venue)

    def path(self):
        return (self.args.competition, f'{self.args.volume:02d}', self.subdir, self.args.venue)

    def build(self):
        super().build()
        for template in ['instructions-inner.tex']:
            jinja.print_template(
                Path(self.launch_directory, *self.path()),
                template, self.context._data, self.output_directory
            )


BuilderNabojVenue().build()
