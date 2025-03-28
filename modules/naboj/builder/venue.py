from pathlib import Path

import core.builder.jinja as jinja
from modules.naboj.builder.builder import BuilderNaboj
from modules.naboj.builder.contexts import BuildableContextVenue


class BuilderNabojVenue(BuilderNaboj):
    _target = 'venue'
    _subdir = 'venues'

    _root_context_class = BuildableContextVenue
    templates = [
        'instructions.jtt',
        'answers-modulo.jtt',
    ]
    language_templates = ['instructions-inner.jtt']

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('venue', type=str)

    def ident(self) -> tuple:
        return self.args.competition, self.args.volume, self.args.venue

    def path(self) -> tuple:
        return self.args.competition, f'{self.args.volume:02d}', self._subdir, self.args.venue

    def build_templates(self):
        super().build_templates()

        for template in self.language_templates:
            path = self.path()
            jinja.print_template(
                Path(self.launch_directory, path[0], path[1], 'languages', self.context.data['venue']['language']), template, self.context.data,
                outdir=self.output_directory,
                new_name=Path(template).with_suffix('.tex'),
            )


BuilderNabojVenue().build_templates()
