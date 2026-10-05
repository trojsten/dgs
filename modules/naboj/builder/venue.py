import logging
from pathlib import Path

import core.utilities.colour as c
from core.builder import jinja
from modules.naboj.builder.builder import BuilderNaboj
from modules.naboj.builder.contexts import BuildableContextVenue

log = logging.getLogger('dgs')


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
        # `launch_directory`, not a path with this machine's home in it. The absolute
        # `/home/kvik/dgs/source/naboj` that used to be here meant the venue builder could only
        # ever run on one computer, and the `-l/--launch` option it ignored is exactly the knob
        # for this.
        source_root = Path(self.launch_directory, *self.language_path())
        language_renderer = jinja.StaticRenderer(source_root)

        for template in self.language_templates:
            # The renderer **returns** the rendered string; it takes no `outfile`. Passing one
            # raised `TypeError: render() got an unexpected keyword argument 'outfile'`, so no
            # venue of any competition had ever been built -- `instructions.pdf` and
            # `answers-modulo.pdf` failed the moment anything asked for them.
            #
            # The name is resolved against `source_root` and so is passed bare, and the render
            # happens before the target is opened, because `open(..., 'w')` truncates at once and
            # a template that raises would otherwise leave a 0-byte `.tex` that make calls fresh.
            if not (source_root / template).exists():
                log.warning(f"No {c.path(template)} for "
                            f"{c.name('/'.join(str(p) for p in self.language_path()))}, skipping it")
                continue
            rendered = language_renderer.render(Path(template), self.context.data)
            with open(self.output_directory / Path(template).with_suffix('.tex'), 'w') as outfile:
                print(rendered, file=outfile)


BuilderNabojVenue().build_templates()
