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
        'tearoff.jtt',
        'envelopes.jtt',
        'instructions.jtt',
        'answers-modulo.jtt',
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
        for template in ['instructions-inner.jtt']:
            jinja.print_template(
                Path(self.launch_directory, *self.path()), template, self.context.data,
                outdir=self.output_directory,
                new_name=Path(template).with_suffix('.tex'),
            )


BuilderNabojVenue().build()
