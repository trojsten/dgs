import abc
import datetime
import zoneinfo
from pathlib import Path

from enschema import Schema

from core import i18n
from core.builder.context.buildable import BuildableFileSystemTreeContext
from core.builder.context.module import ContextModule
from core.builder.renderer import ConstantsContext
from core.i18n import Locale

from .base import ContextNaboj
from .hierarchy import ContextCompetition, ContextLanguage, ContextVenue, ContextVolume
from .i18n import ContextI18nGlobal
from .validators import NabojValidator


def local_start(date: datetime.date, start: int, source: str, target: str) -> int:
    """
    The minute of the day in `target` at which `start` minutes into `date` in `source` falls.
    Every venue begins at one moment; only the clock on the wall differs. The date matters,
    because two zones need not change to summer time on the same day.
    """
    moment = datetime.datetime.combine(date, datetime.time(start // 60, start % 60),
                                       tzinfo=zoneinfo.ZoneInfo(source))
    local = moment.astimezone(zoneinfo.ZoneInfo(target))
    if local.date() != date:
        raise ValueError(f"Starting at {start // 60:02d}:{start % 60:02d} in {source} "
                         f"puts {target} on {local.date()}, not on the competition's day")
    return local.hour * 60 + local.minute


class BuildableContextNaboj(BuildableFileSystemTreeContext, ContextNaboj, metaclass=abc.ABCMeta):
    _schema = ContextNaboj._schema
    _validator_class = NabojValidator

    def populate(self, competition, volume):
        super().populate(competition)
        self.adopt(
            module=ContextModule('naboj'),
            competition=ContextCompetition(self.root, competition),
            volume=ContextVolume(self.root, competition, volume),
        )


class BuildableContextLanguage(BuildableContextNaboj):
    _target = 'language'
    _subdir = 'languages'
    _schema = Schema({})

    def __init__(self, root, *args):
        self._schema = super()._schema | self._schema
        super().__init__(root, *args)

    def populate(self, competition, volume, language):
        super().populate(competition, volume)
        self.adopt(
            language=ContextLanguage(self.root, competition, volume, language),
            i18n=ContextI18nGlobal(self.root, competition),
            constants=ConstantsContext('constants', Path('core/data/constants.yaml'))
        )


class BuildableContextVenue(BuildableContextNaboj):
    _target = 'venue'
    _subdir = 'venues'
    _schema = Schema({
        'language': Locale.schema,
    })

    def __init__(self, root, *args):
        self._schema = super()._schema | self._schema
        super().__init__(root, *args)

    def populate(self, competition, volume, venue):
        super().populate(competition, volume)
        self.adopt(
            venue=ContextVenue(self.root, competition, volume, venue),
            i18n=ContextI18nGlobal(self.root, competition)
        ).add(language=i18n.languages[self.data['venue']['language']].as_dict())

        volume, venue = self.data['volume'], self.data['venue']
        venue.setdefault('timezone', volume['timezone'])
        if 'start' not in venue:
            venue['start'] = local_start(volume['date'], volume['start'], volume['timezone'], venue['timezone'])
