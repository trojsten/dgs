import os
import sys
from pathlib import Path

sys.path.append('.')

from core.utilities import context


class ContextI18n(context.Context):
    def __init__(self, root, competition, language):
        super().__init__()
        self.load_YAML(root, competition, '.static', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.Context):
    def __init__(self, root, competition):
        super().__init__()
        for language in ['sk', 'cs', 'hu', 'pl', 'en', 'ru', 'fa', 'es']: # Change this to scan the i18n directory
            self.absorb(language, ContextI18n(root, competition, language))


class ContextNaboj(context.Context):
    def node_path(self, root, competition='', volume='', target_type='', target=''):
        return Path(root, competition, f"{volume:02d}" if volume != '' else '', target_type, target)


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
        self.add({'problems_modulo': context.split_mod(self.data['problems'], self.data['evaluators'], 1)})


class ContextLanguage(ContextNaboj):
    def __init__(self, language):
        super().__init__()
        self.add_id(language)
        self.add({'polyglossia': {
                'sk': 'slovak',
                'en': 'english',
                'cs': 'czech',
                'hu': 'magyar',
                'pl': 'polish',
                'ru': 'russian',
                'fa': 'persian',
                'es': 'spanish',
            }[language]}
        )
        self.add({'rtl': True if language == 'fa' else False})


class ContextVenue(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        comp = ContextCompetition(root, competition)
        self.load_meta(root, competition, volume, 'venues', venue).add_id(venue)
        self.add({'teams_grouped': context.split_div(context.numerate(self.data.get('teams')), comp.data['tearoff']['per_page'])})


class ContextBooklet(ContextNaboj):
    def __init__(self, root, competition, volume, language):
        super().__init__()
        self.load_meta(root, competition, volume, 'languages', language)
        self.absorb('module', ContextModule('naboj'))
        self.absorb('competition', ContextCompetition(root, competition))
        self.absorb('volume', ContextVolume(root, competition, volume))
        self.absorb('language', ContextLanguage(language))
        self.absorb('i18n', ContextI18n(root, competition, language))


class ContextTearoff(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.absorb('module', ContextModule('naboj'))
        self.absorb('competition', ContextCompetition(root, competition))
        self.absorb('volume', ContextVolume(root, competition, volume))
        self.absorb('venue', ContextVenue(root, competition, volume, venue))
        self.absorb('i18n', ContextI18nGlobal(root, competition))
