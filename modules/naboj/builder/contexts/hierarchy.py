import datetime
import itertools
import pprint

from enschema import Schema, And, Or, Optional, Regex

from core import i18n
from core.utilities import lists
from core.utilities.schema import valid_language, valid_language_name
from core.builder.validator import String
from .base import ContextNaboj


class ContextCompetition(ContextNaboj):
    _schema = Schema({
        'id': String,
        'tearoff': {
            'per_page': int,
            'height': int,
            'team_space': int,
            'barcode_space': int,
            'bottomsep': int,
            'inner': int,
        },
        'organisation': {
            'name': String,
            'address': String,
        },
        'constants': {
            str: {
                'symbol': str,
                'value': Or(int, float),
                'unit': str,
                'exact': Or(int, float),
                'digits': int,
                Optional('siextra'): str,
            }
        },
        'url': String,
        'hacks': dict,
    })

    def populate(self, competition):
        super().populate(competition)
        self.load_meta(competition) \
            .add_id(competition)


class ContextLanguage(ContextNaboj):
    _target = 'language'
    _subdir = 'languages'
    _schema = Schema({
        'id': valid_language,
        'booklet': {
            'contents': {
                'intro': bool,
                'problems': bool,
                'solutions': bool,
                'answers': bool,
            }
        },
        'name': valid_language_name,
        'rtl': bool,
    })

    def populate(self, competition, volume, language):
        super().populate(competition)
        self.load_meta(competition, volume, language) \
            .add_id(language) \
            .add(
                name=i18n.languages[language].name,
                rtl=i18n.languages[language].rtl,
            )


class ContextVenue(ContextNaboj):
    _target = 'venue'
    _subdir = 'venues'
    _schema = Schema({
        'id': And(str, len),
        'code': Regex(r'[A-Z]{5}'),
        'name': And(str, len),
        'language': valid_language,
        'problems_modulo': [[ContextNaboj.problem]],
        Optional('orgs'): [And(str, len)],
        'evaluators': int,
        'start': And(int, lambda x: 0 <= x < 1440),
    })

    def populate(self, competition, volume, venue):
        super().populate(competition)
        comp = ContextCompetition(self.root, competition)
        vol = ContextVolume(self.root, competition, volume)
        self.load_meta(competition, volume, venue) \
            .add_id(venue)
        self.add(
            problems_modulo=lists.split_mod(
                lists.add_numbers([x['id'] for x in vol.data['problems']], itertools.count(1)),
                self.data['evaluators'], first=1,
            ),
        )


class ContextVolume(ContextNaboj):
    _schema = Schema({
        'id': And(str, len),
        'number': And(int, lambda x: x >= 0),
        'date': datetime.date,
        'authors': {
            'problems': [str],
            'pictures': [str],
            'editors': [str],
            'head': str,
        },
        Optional('venues'): {
            str: {
                'head': str,
                'name': str,
            }
        },
        'problems': [ContextNaboj.problem],
        'constants': dict,
        'table': int,
        'start': And(int, lambda x: 0 <= x < 1440),
    })

    def populate(self, competition, volume):
        super().populate(competition)
        self.load_meta(competition, volume) \
            .add_id(f'{volume:02d}') \
            .add_number(volume)

        self.add(problems=lists.add_numbers(self.data['problems'], itertools.count(1)))
