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
                'value': Or(str, int, float),
                'unit': str,
                Optional('siextra'): str,
            }
        },
        'url': String,
        'founded': int,
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
        'teams': [ContextNaboj.team],
        'teams_grouped': [[ContextNaboj.team]],
        'problems_modulo': [[ContextNaboj.problem]],
        Optional('orgs'): [And(str, len)],
        'evaluators': int,
        'start': And(int, lambda x: 0 <= x < 1440),
    })

    def _add_extra_teams(self, competition, venue):
        code = 0
        while len(self.data['teams']) % competition.data['tearoff']['per_page'] != 0:
            self.data['teams'].append({
                'id': 0,
                'code': f'SKBAS{999 - code}',
                'contact_email': "none@none.none",
                'contact_name': "Unnamed",
                'contact_phone': "",
                'contestants': "unknown",
                'display_name': f"Extra set {999 - code}",
                'in_school_symbol': None,
                'language': self.data['language'],
                'name': "",
                'number': 0,
                'school': f"Extra set {999 - code}",
                'school_address': "",
                'school_id': 0,
                'school_name': f"Extra set {999 - code}",
                'status': 'R',
                'venue': self.data['id'],
                'venue_code': self.data['code'],
                'venue_id': 0,
                #'venue_id': self.data['id'], # Currently there is a collision with venue.id from web!!! Fix later
            })
            code += 1

    def populate(self, competition, volume, venue):
        super().populate(competition)
        comp = ContextCompetition(self.root, competition)
        vol = ContextVolume(self.root, competition, volume)
        self.load_meta(competition, volume, venue) \
            .add_id(venue)
        self._add_extra_teams(comp, vol)
        self.add(
            teams=lists.numerate(self.data.get('teams'), itertools.count(0)),
            teams_grouped=lists.split_div(
                lists.numerate(self.data.get('teams')), comp.data['tearoff']['per_page']
            ),
            problems_modulo=lists.split_mod(
                lists.add_numbers([x['id'] for x in vol.data['problems']], itertools.count(1)),
                self.data['evaluators'], first=1,
            ),
        )


class ContextVolume(ContextNaboj):
    _schema = Schema({
        'id': And(str, len),
        'number': And(int, lambda x: x > 0),
        'date': datetime.date,
        'authors': [str],
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
