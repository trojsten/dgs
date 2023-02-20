import pprint
from schema import Schema, And

from .hierarchy import ContextNaboj, ContextModule, ContextCompetition, ContextVolume, ContextLanguage, ContextVenue
from .i18n import ContextI18n, ContextI18nGlobal


class ContextBooklet(ContextNaboj):
    schema = Schema({
        'booklet': {
            'contents': {
                'intro': bool,
                'problems': bool,
                'solutions': bool,
                'answers': bool,
            }
        },
    })

    def populate(self, competition, volume, language):
        self.load_meta(competition, volume, 'languages', language)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(self.root, competition))
        self.adopt('volume', ContextVolume(self.root, competition, volume))
        self.adopt('language', ContextLanguage(self.root, language))
        self.adopt('i18n', ContextI18n(self.root, competition, language))


class ContextTearoff(ContextNaboj):
    def populate(self, competition, volume, venue):
        super().populate(competition, volume, venue)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(self.root, competition))
        self.adopt('volume', ContextVolume(self.root, competition, volume))
        self.adopt('venue', ContextVenue(self.root, competition, volume, venue))
        self.adopt('i18n', ContextI18nGlobal(self.root, competition))
        pprint.pprint(self.data)
