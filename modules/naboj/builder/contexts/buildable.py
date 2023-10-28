import pprint
import abc
from schema import Schema, And, Optional

import core.utilities.globals as glob
from core.builder.context import BuildableContext, ContextModule
from .base import ContextNaboj
from .hierarchy import ContextCompetition, ContextVolume, ContextLanguage, ContextVenue
from .i18n import ContextI18n, ContextI18nGlobal


class BuildableContextNaboj(BuildableContext, ContextNaboj, metaclass=abc.ABCMeta):
    schema = Schema({})  # Nothing to be read directly

    def populate(self, competition, volume, venue):
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(self.root, competition))
        self.adopt('volume', ContextVolume(self.root, competition, volume))


class BuildableContextLanguage(BuildableContextNaboj):
    target = 'language'
    subdir = 'languages'

    def populate(self, competition, volume, language):
        super().populate(competition, volume, language)
        self.adopt('language', ContextLanguage(self.root, competition, volume, language))
        self.adopt('i18n', ContextI18nGlobal(self.root, competition))


class BuildableContextVenue(BuildableContextNaboj):
    target = 'venue'
    subdir = 'venues'
    schema = Schema({
        'language': {
            'id': str,
            'polyglossia': str,
            Optional('rtl'): bool,
        }
    })

    def populate(self, competition, volume, venue):
        super().populate(competition, volume, venue)
        self.adopt('venue', ContextVenue(self.root, competition, volume, venue).override('start', self.data['volume']))
        self.adopt('i18n', ContextI18nGlobal(self.root, competition))
        self.add({
            'language': {
                'id': self.data['venue']['language'],
            } | glob.languages[self.data['venue']['language']]
        })

        if not 'start' in self.data['venue']:
            self.data['venue']['start'] = self.data['volume']['start']
