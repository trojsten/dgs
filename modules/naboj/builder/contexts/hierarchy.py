import datetime
import itertools
import zoneinfo

from enschema import And, Optional, Regex, Schema

from core import i18n
from core.builder.validator import String
from core.utilities import lists
from core.utilities.schema import valid_language, valid_language_name, valid_timezone

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
        'url': String,
        # Who the colophon names after the copyright sign. It was written into
        # `blocks/colophon.jtex` as "Náboj Physics international team", which is true of one
        # competition and of no other -- chem's booklets claimed it too.
        'rights_holder': String,
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
            },
        },
        Optional('translators', default=[]): [str],
        'name': valid_language_name,
        'rtl': bool,
    })

    def populate(self, competition, volume, language):
        super().populate(competition)
        self.load_meta(competition, volume, language) \
            .add_id(language) \
            .add(
                name=i18n.languages[language].full,
                rtl=i18n.languages[language].rtl,
            )


def local_minutes(utc_minutes: int, date: datetime.date, zone: str) -> int:
    """
    The volume's UTC start as a wall clock in `zone`, in minutes past midnight.

    The date is the volume's, and it is not decoration: an offset is a function of the instant,
    not of the place. Náboj runs in November under CET and chem in April under CEST, and Moscow
    was UTC+4 from 2011 to 2014, so volumes 21 and 22 convert differently from the same zone.
    Reading the zone's *current* offset instead would quietly re-time the archive.

    Only the clock is returned. A conversion can cross midnight -- it does not for any venue
    this competition has ever had, where the extremes are Lisbon and Moscow -- and the printed
    sentence says a time, not a date, so the day is the venue's own business.
    """
    moment = datetime.datetime.combine(
        date, datetime.time(utc_minutes // 60, utc_minutes % 60),
        tzinfo=datetime.UTC).astimezone(zoneinfo.ZoneInfo(zone))
    return moment.hour * 60 + moment.minute


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
        # **The zone, and only the zone, is the venue's own business.** A venue sits where it
        # sits; when the competition begins is the volume's decision, and `start` here is the
        # exception a venue is allowed rather than the rule it has to restate -- 102 of the 117
        # venue metas repeated the volume's time, and the one venue that did mean something
        # else by it, `28/lisboa` at 10:30, was overwritten with the volume's 11:30 before it
        # ever reached the page.
        'timezone': And(str, valid_timezone),
        # **UTC, like the volume's**, and in minutes past midnight. See `ContextVolume`.
        Optional('start'): And(int, lambda x: 0 <= x < 1440),
    })

    def populate(self, competition, volume, venue):
        super().populate(competition)
        ContextCompetition(self.root, competition)
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
        # `chem/01`, `phys/02` and `phys/03` predate the `authors` block and list their people
        # under `orgs` instead. Those are real names; admitting the key keeps them rather than
        # forcing a choice between deleting them and inventing which of them wrote problems.
        Optional('orgs'): [str],
        Optional('venues'): {
            str: {
                'head': str,
                'name': str,
            }
        },
        'workshop': str,
        'problems': [ContextNaboj.problem],
        'constants': dict,
        'table': int,
        # **Minutes past midnight, UTC** -- the instant the envelopes are opened, which is one
        # instant however many countries the volume runs in. What each venue prints is this
        # moment on its own clock, computed by `BuildableContextVenue` from its `timezone`, so
        # a volume in Lisbon and Uzhhorod says one thing here and prints two different times.
        # `11:30` is YAML 1.1 sexagesimal and loads as 690, which is why the key is an int.
        'start': And(int, lambda x: 0 <= x < 1440),
    })

    def populate(self, competition, volume):
        super().populate(competition)
        self.load_meta(competition, volume) \
            .add_id(f'{volume:02d}') \
            .add_number(volume)

        self.add(problems=lists.add_numbers(self.data['problems'], itertools.count(1)))
