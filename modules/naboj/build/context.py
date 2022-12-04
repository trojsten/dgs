import os
import sys
import glob
import itertools
from pathlib import Path

from core.build import context
from core.utils import lists


class ContextI18n(context.Context):
    def __init__(self, root, competition, language):
        super().__init__()
        self.load_YAML(root, competition, '.static', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.Context):
    def __init__(self, root, competition):
        super().__init__()
        for language in [x.stem for x in Path(root, competition, '.static', 'i18n').glob('*.yaml')]:
            self.adopt(language, ContextI18n(root, competition, language))


class ContextNaboj(context.Context):
    def node_path(self, root, competition=None, volume=None, target_type=None, target=None):
        return Path(
            '' if root is None else root,
            '' if competition is None else competition,
            '' if volume is None else f'{volume:02d}',
            '' if target_type is None else target_type,
            '' if target is None else target
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
        self.load_meta(root, competition, volume) \
            .add_id(f'{volume:02d}') \
            .add_number(volume)

        self.add(
            dict(problems=lists.add_numbers(self.data['problems'], itertools.count(1))),
            dict(problems_modulo=lists.split_mod(
                lists.add_numbers(self.data['problems'], itertools.count(1)), self.data['evaluators'], first=1
            )),
        )
        self.add_subdirs(ContextVenue, 'venues', (root, competition, volume), (root, competition, volume, 'venues'))


class ContextLanguage(ContextNaboj):
    def __init__(self, language):
        super().__init__()
        self.add_id(language)
        self.add(
            {
                'polyglossia': {
                    'sk': 'slovak',
                    'en': 'english',
                    'cs': 'czech',
                    'hu': 'magyar',
                    'pl': 'polish',
                    'ru': 'russian',
                    'fa': 'persian',
                    'es': 'spanish',
                }[language]
            }
        )
        self.add({'rtl': True if language == 'fa' else False})


class ContextVenue(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        comp = ContextCompetition(root, competition)
        self.load_meta(root, competition, volume, 'venues', venue).add_id(venue)
        self.add({'teams_grouped': lists.split_div(lists.numerate(self.data.get('teams')), comp.data['tearoff']['per_page'])})


class ContextBooklet(ContextNaboj):
    def __init__(self, root, competition, volume, language):
        super().__init__()
        self.load_meta(root, competition, volume, 'languages', language)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('language', ContextLanguage(language))
        self.adopt('i18n', ContextI18n(root, competition, language))


class ContextTearoff(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('venue', ContextVenue(root, competition, volume, venue))
        self.adopt('i18n', ContextI18nGlobal(root, competition))
