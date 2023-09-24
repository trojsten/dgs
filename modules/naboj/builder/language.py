from pathlib import Path

import builder
import core.builder.jinja as jinja
from modules.naboj.builder.contexts import ContextBooklet


class BuilderNabojLanguage(builder.BuilderNaboj):
    target = 'language'
    subdir = 'languages'

    root_context_class = ContextBooklet
    templates = [
        'booklet.tex',
        'answers.tex',
        'answers-modulo.tex',
        'constants.tex',
        'cover.tex',
        'instructions.tex',
        'instructions-online.tex',
        'online.tex',
    ]

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-l', '--language', type=str)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.language)

    def path(self):
        return (self.args.competition, f'{self.args.volume:02d}', self.subdir, self.args.language)

    def build(self):
        super().build()
        for template in ['intro.tex', 'instructions-inner.tex']:
            jinja.print_template(
                Path(self.launch_directory, *self.path(), '_extras'),
                template, self.context.data, self.output_directory
            )


BuilderNabojLanguage().build()
