from pathlib import Path

from core.builder import jinja
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

    def build_templates(self, *, new_name: str | None = None) -> None:
        super().build_templates(new_name=new_name)
        language_root = Path(self.launch_directory, 'source', 'naboj', *self.language_path())
        language_renderer = jinja.StaticRenderer(language_root)

        for template in self.language_templates:
            if not (language_root / template).exists():
                continue
            rendered = language_renderer.render(Path(template), self.context.data)
            with open(self.output_directory / Path(template).with_suffix('.tex'), 'w') as outfile:
                print(rendered, file=outfile)


BuilderNabojVenue().build_templates()
