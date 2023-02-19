import os
import sys
import glob
import itertools
import datetime
from pathlib import Path
from schema import Schema, And, Or, Optional, Regex

from core.builder import context
from core.utils import lists
from core.utils.schema import valid_language, string
import core.utils.globals as glob

from contexts import ContextI18n, ContextI18nGlobal, ContextNaboj


class ContextModule(ContextNaboj):
    schema = Schema({'id': string})

    def populate(self, module):
        self.add_id(module)


class ContextCompetition(ContextNaboj):
    schema = Schema({
        'id':               string,
        'founded':          And(int, lambda x: x >= 1950),
        'tearoff':          {
                                'per_page': int,
                                'height': int,
                                'team_space': int,
                                'barcode_space': int,
                                'bottomsep': int,
                                'inner': int,
                            },
        'organisation':     {
                                'name': string,
                                'address': string,
                            },
        'constants':        {
                                str: {
                                    'symbol': str,
                                    'value': Or(str, int, float),
                                    'unit': str,
                                }
                            },
        'URL':              And(str, len),
        'full':             {'nominative': str, 'genitive': str, 'locative': str},
        'hacks':            dict,
    })

    def populate(self, root, competition):
        self.name(competition)
        self.load_meta(root, competition) \
            .add_id(competition)


class ContextLanguage(ContextNaboj):
    schema = Schema({
        'id': valid_language,
        'polyglossia': lambda x: x in [lang['polyglossia'] for lang in glob.languages.values()],
        'rtl': bool,
    })

    def populate(self, language):
        self.name(language)
        self.add_id(language)
        self.add({'polyglossia': glob.languages[language]['polyglossia']})
        self.add({'rtl': glob.languages[language].get('rtl', False)}),


class ContextVenue(ContextNaboj):
    schema = Schema({
        'id':       And(str, len),
        'name':     And(str, len),
        'teams':    [ContextNaboj.team],
        'teams_grouped': [[ContextNaboj.team]],
    })

    def populate(self, root, competition, volume, venue):
        self.name(competition, volume, venue)
        comp = ContextCompetition(root, competition)
        self.load_meta(root, competition, volume, 'venues', venue).add_id(venue)
        self.add({'teams_grouped': lists.split_div(lists.numerate(self.data.get('teams')), comp.data['tearoff']['per_page'])})


class ContextVolume(ContextNaboj):
    schema = Schema({
        'id': And(str, len),
        'number': And(int, lambda x: x > 0),
        'start': int,
        'date': datetime.date,
        'orgs': [str],
        'problems': [ContextNaboj.problem],
        'problems_modulo': [[ContextNaboj.problem]],
        'constants': dict,
        'evaluators': int,
        'venues': [ContextVenue.schema],
    })

    def populate(self, root, competition, volume):
        self.name(competition, volume)
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

    def populate(self, root, competition, volume, language):
        self.name(competition, volume, venue)
        self.load_meta(competition, volume, 'languages', language)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('language', ContextLanguage(language))
        self.adopt('i18n', ContextI18n(root, competition, language))


class ContextTearoff(ContextNaboj):
    schema = Schema({})

    def populate(self, root, competition, volume, venue):
        self.name(competition, volume, venue)
        self.adopt('module', ContextModule('naboj'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('venue', ContextVenue(root, competition, volume, venue))
        self.adopt('i18n', ContextI18nGlobal(root, competition))
