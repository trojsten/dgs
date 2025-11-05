from pathlib import Path

import core.builder.jinja as jinja
from modules.naboj.builder.builder import BuilderNaboj
from modules.naboj.builder.contexts import BuildableContextVenue


class BuilderNabojVenue(BuilderNaboj):
    _target = 'venue'
    _subdir = 'venues'

    _root_context_class = BuildableContextVenue
    templates = [
        'instructions.jtex',
        'answers-modulo.jtex',
    ]
    language_templates = [
        'instructions-inner.jtex'
    ]

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('venue', type=str)

    def ident(self) -> tuple:
        return self.args.competition, self.args.volume, self.args.venue

    def path(self) -> tuple:
        return self.args.competition, f'{self.args.volume:02d}', self._subdir, self.args.venue

    def language_path(self) -> tuple:
        return self.args.competition, f'{self.args.volume:02d}', 'languages', self.context.data['language']['id']

    def build_templates(self):
        super().build_templates()
        language_renderer = jinja.StaticRenderer(Path('/home/kvik/dgs/source/naboj') / Path(*self.language_path()))

        for template in self.language_templates:
            outfile = open(self.output_directory / Path(template).with_suffix('.tex'), 'w')
            infile = Path('source/naboj') / Path(*self.language_path()) / template
            language_renderer.render(infile, self.context.data, outfile=outfile)


BuilderNabojVenue().build_templates()
