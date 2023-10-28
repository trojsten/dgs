import pprint
from schema import Schema, And

import core.utilities.globals as glob
from core.builder.context import BuildableContext, ContextModule
from .hierarchy import ContextNaboj, ContextCompetition, ContextVolume, ContextLanguage, ContextVenue
from .i18n import ContextI18n, ContextI18nGlobal


class ContextBooklet(BuildableContext, ContextNaboj):
    target = 'language'
    subdir = 'languages'
    schema = Schema({})  # Nothing to be read directly

    def populate(self, competition, volume, language):
        super().populate(competition, volume, language)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(self.root, competition))
        self.adopt('volume', ContextVolume(self.root, competition, volume))
        self.adopt('language', ContextLanguage(self.root, competition, volume, language))
        self.adopt('i18n', ContextI18nGlobal(self.root, competition))
        self.add({
            'language': glob.languages[language] | {'id': language}
        })

class ContextTearoff(BuildableContext, ContextNaboj):
    target = 'venue'
    subdir = 'venues'
    schema = Schema({
        'language': dict,
    })  # Nothing to be read directly

    def populate(self, competition, volume, venue):
        super().populate(competition, volume, venue)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(self.root, competition))
        self.adopt('volume', ContextVolume(self.root, competition, volume))
        self.adopt('venue', ContextVenue(self.root, competition, volume, venue))
        self.adopt('i18n', ContextI18nGlobal(self.root, competition))
        self.add({
            'language': glob.languages[self.data['venue']['language']] | {'id': self.data['venue']['language']}
        })
