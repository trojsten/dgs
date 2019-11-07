import os
import sys

sys.path.append('.')

from core.utilities import context


class BuilderNaboj(context.BaseBuilder):
    module = 'naboj'

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('-c', '--competition', choices=['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
        self.parser.add_argument('-v', '--volume', type=int)


class ContextI18n(context.Context):
    def __init__(self, language):
        super().__init__()
        self.load_YAML(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'templates', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.Context):
    def __init__(self):
        super().__init__()
        for language in ['slovak', 'czech', 'hungarian', 'polish', 'english', 'russian']:
            self.absorb(language, ContextI18n(language))


class ContextNaboj(context.Context):
    def nodePath(self, root, competition=None, volume=None, target_type=None, target=None):
        return os.path.join(
            root,
            '' if competition is None else competition,
            '' if volume is None else f'{volume:02d}',
            '' if target_type is None else target_type,
            '' if target is None else target,
        )


class ContextModule(ContextNaboj):
    def __init__(self, module):
        super().__init__()
        self.add_id(module)


class ContextCompetition(ContextNaboj):
    def __init__(self, root, competition):
        super().__init__()
        self.load_meta(root, competition) \
            .add_id(competition)


class ContextVolume(ContextNaboj):
    def __init__(self, root, competition, volume):
        super().__init__()
        self.id = '{:02d}'.format(volume)
        self.load_meta(root, competition, volume) \
            .add_id(self.id) \
            .add_number(volume)

        self.add({'problems': context.add_numbers(self.data['problems'], 1)})
        self.add({'problems_mod_5': context.split_mod(self.data['problems'], 5, 1)})


class ContextLanguage(ContextNaboj):
    def __init__(self, language):
        super().__init__()
        self.add_id(language)
        self.add({'polyglossia': 'magyar' if language == 'hungarian' else language})


class ContextVenue(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.load_meta(root, competition, volume, 'venues', venue).add_id(venue)
        self.add({'teams_div_3': context.split_div(context.numerate(self.data.get('teams')), 3)})


class ContextBooklet(ContextNaboj):
    def __init__(self, root, competition, volume, language):
        super().__init__()
        self.load_meta(root, competition, volume, 'languages', language)
        self.absorb('module', ContextModule('naboj'))
        self.absorb('competition', ContextCompetition(root, competition))
        self.absorb('volume', ContextVolume(root, competition, volume))
        self.absorb('language', ContextLanguage(language))
        self.absorb('i18n', ContextI18n(language))


class ContextTearoff(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.absorb('module', ContextModule('naboj'))
        self.absorb('competition', ContextCompetition(root, competition))
        self.absorb('volume', ContextVolume(root, competition, volume))
        self.absorb('venue', ContextVenue(root, competition, volume, venue))
        self.absorb('i18n', ContextI18nGlobal())
