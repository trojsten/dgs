import datetime
import itertools
from schema import Schema, And, Or

import core.utilities.globals as glob
from core.utilities import lists
from core.utilities.schema import string, valid_language
from .base import ContextNaboj


class ContextCompetition(ContextNaboj):
    schema = Schema({
        'id': string,
        'founded': And(int, lambda x: x >= 1950),
        'tearoff': {
            'per_page': int,
            'height': int,
            'team_space': int,
            'barcode_space': int,
            'bottomsep': int,
            'inner': int,
        },
        'organisation': {
            'name': string,
            'address': string,
        },
        'constants': {
            str: {
                'symbol': str,
                'value': Or(str, int, float),
                'unit': str,
            }
        },
        'URL': And(str, len),
        'full': {
            'nominative': str,
            'genitive': str,
            'locative': str
        },
        'hacks': dict,
    })

    def populate(self, competition):
        self.load_meta(competition) \
            .add_id(competition)


class ContextLanguage(ContextNaboj):
    target = 'language'
    subdir = 'languages'
    schema = Schema({
        'id': valid_language,
        'booklet': {
            'contents': {
                'intro': bool,
                'problems': bool,
                'solutions': bool,
                'answers': bool,
            }
        },
        'polyglossia': lambda x: x in [lang['polyglossia'] for lang in glob.languages.values()],
        'rtl': bool,
    })

    def populate(self, competition, volume, language):
        self.load_meta(competition, volume, self.subdir, language) \
            .add_id(language)
        self.add({'polyglossia': glob.languages[language]['polyglossia']})
        self.add({'rtl': glob.languages[language].get('rtl', False)}),


class ContextVenue(ContextNaboj):
    target = 'venue'
    subdir = 'venues'
    schema = Schema({
        'id': And(str, len),
        'name': And(str, len),
        'teams': [ContextNaboj.team],
        'teams_grouped': [[ContextNaboj.team]],
    })

    def populate(self, competition, volume, venue):
        comp = ContextCompetition(self.root, competition)
        self.load_meta(competition, volume, self.subdir, venue) \
            .add_id(venue)
        self.add({
            'teams': lists.numerate(self.data.get('teams'), itertools.count(0)),
            'teams_grouped': lists.split_div(
                lists.numerate(self.data.get('teams')), comp.data['tearoff']['per_page']
            )
        })


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
        'table': int,
    })

    def populate(self, competition, volume):
        self.load_meta(competition, volume) \
            .add_id(f'{volume:02d}') \
            .add_number(volume)

        self.add(
            dict(problems=lists.add_numbers(self.data['problems'], itertools.count(1))),
            dict(problems_modulo=lists.split_mod(
                lists.add_numbers(self.data['problems'], itertools.count(1)), self.data['evaluators'], first=1
            )),
        )
