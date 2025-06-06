from pathlib import Path

import core.builder.jinja as jinja
from modules.naboj.builder.builder import BuilderNaboj
from modules.naboj.builder.contexts import BuildableContextVenue


class BuilderNabojVenue(BuilderNaboj):
    _target = 'venue'
    _subdir = 'venues'

    _root_context_class = BuildableContextVenue
    templates = [
        'instructions.jinja.tex',
        'answers-modulo.jinja.tex',
    ]
    language_templates = []

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('venue', type=str)

    def ident(self) -> tuple:
        return self.args.competition, self.args.volume, self.args.venue

    def path(self) -> tuple:
        return self.args.competition, f'{self.args.volume:02d}', self._subdir, self.args.venue

    def build_templates(self):
        super().build_templates()
        renderer = jinja.StaticRenderer(Path(self.launch_directory, *self.path()))

        for template in self.language_templates:
            path = self.path()
            outfile = open(self.output_directory / Path(template).with_suffix('.tex'), 'w')
            renderer.render(template, self.context.data['venue']['language'], outfile=outfile)


BuilderNabojVenue().build_templates()
