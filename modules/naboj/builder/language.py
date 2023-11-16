import builder
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
    i18n_templates = ['intro.jtt']

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('language', type=str)

    def id(self):
        return self.args.competition, self.args.volume, self.args.language

    def path(self):
        return self.args.competition, f'{self.args.volume:02d}', self.subdir, self.args.language


BuilderNabojLanguage().build()
