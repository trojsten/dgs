import os

import builder
import context

import core.utilities.jinja as jinja


class BuilderNabojLanguage(builder.BuilderNaboj):
    target = 'language'
    subdir = 'languages'

    root_context_class = context.ContextBooklet
    templates = [
        'booklet.tex',
        'answers.tex',
        'answers-mod5.tex',
        'constants.tex',
        'cover.tex',
        'instructions.tex',
        'online.tex',
    ]

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-l', '--language', type=str)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.language)

    def path(self):
        return (self.args.competition, '{:02d}'.format(self.args.volume), self.subdir, self.args.language)

    def build(self):
        super().build()
        for template in ['intro.tex', 'instructions-text.tex']:
            jinja.print_template(
                os.path.join(self.launch_directory, self.args.competition, '{:02d}'.format(self.args.volume), 'languages', self.args.language),
                template, self.context.data, self.output_directory
            )


BuilderNabojLanguage().build()
