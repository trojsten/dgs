from pathlib import Path

import builder
import core.builder.jinja as jinja
from modules.naboj.builder.contexts import BuildableContextLanguage


class BuilderNabojLanguage(builder.BuilderNaboj):
    target = 'language'
    subdir = 'languages'

    root_context_class = BuildableContextLanguage
    templates = [
        'booklet.jtt',
        'answers.jtt',
        'constants.jtt',
        'cover.jtt',
        'instructions-online.jtt',
        'online.jtt',
    ]

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('language', type=str)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.language)

    def path(self):
        return (self.args.competition, f'{self.args.volume:02d}', self.subdir, self.args.language)

    def build(self):
        super().build()
        for template in ['intro.jtt']:
            jinja.print_template(
                Path(self.launch_directory, *self.path(), '_extras'), template, self.context.data,
                outdir=self.output_directory,
                new_name=Path(template).with_suffix('.tex'),
            )


BuilderNabojLanguage().build()
