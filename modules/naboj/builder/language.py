from modules.naboj.builder.builder import BuilderNaboj
from modules.naboj.builder.contexts import BuildableContextLanguage


class BuilderNabojLanguage(BuilderNaboj):
    _target = 'language'
    _subdir = 'languages'

    _root_context_class = BuildableContextLanguage
    templates = [
        'booklet.jtt',
        'answers.jtt',
        'constants.jtt',
        'cover.jtt',
        'instructions-online.jtt',
        'online.jtt',
        'tearoff.jtt',
    ]
    i18n_templates = ['intro.jtt']

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('language', type=str)

    def ident(self):
        return self.args.competition, self.args.volume, self.args.language

    def path(self):
        return self.args.competition, f'{self.args.volume:02d}', self._subdir, self.args.language


BuilderNabojLanguage().build_templates()
