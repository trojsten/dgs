import logging
import sys
from pathlib import Path

sys.path.append('.')

import builder
import core.builder.jinja as jinja
import core.utilities.logger as logger
from modules.naboj.builder.contexts import BuildableContextVenue


log = logging.getLogger('dgs')


class BuilderNabojVenue(builder.BuilderNaboj):
    _target = 'venue'
    _subdir = 'venues'

    _root_context_class = BuildableContextVenue
    templates = [
        'barcodes.jtt',
        'tearoff.jtt',
        'envelopes.jtt',
        'instructions.jtt',
        'answers-modulo.jtt',
    ]
    language_templates = ['instructions-inner.jtt', 'evaluators.jtt']

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('venue', type=str)

    def id(self):
        return self.args.competition, self.args.volume, self.args.venue

    def path(self):
        return self.args.competition, f'{self.args.volume:02d}', self._subdir, self.args.venue

    def build(self):
        super().build()

        for template in self.language_templates:
            path = self.path()
            jinja.print_template(
                Path(self.launch_directory, path[0], path[1], 'languages', 'sk'), template, self.context.data,
                outdir=self.output_directory,
                new_name=Path(template).with_suffix('.tex'),
            )


BuilderNabojVenue().build()
