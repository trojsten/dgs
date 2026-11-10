import abc
from pathlib import Path

from enschema import Schema

from core import i18n
from core.builder.context.buildable import BuildableFileSystemTreeContext
from core.builder.context.module import ContextModule
from core.builder.renderer import ConstantsContext
from core.i18n import Locale

from .base import ContextNaboj
from .hierarchy import (
    ContextCompetition,
    ContextLanguage,
    ContextVenue,
    ContextVolume,
    local_minutes,
)
from .i18n import ContextI18nGlobal
from .validators import NabojValidator


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
        """
        **`venue.start` reaches a template as the venue's own wall clock**, not as the UTC the
        meta records. Every language's `instructions-inner.jtex` prints it as
        `(* venue.start // 60 *):(* venue.start % 60 *)` and a contestant reads the clock on
        the wall, so the conversion belongs here rather than in nine translated templates.

        What it replaced was `.override('start', volume['start'])`, which overwrote the venue's
        own value unconditionally -- so a venue's `start:` had never once reached the page, and
        `28/lisboa` printed 11:30 for the four years its meta said 10:30. The fallback below it,
        `if 'start' not in ...`, could not run for the same reason. A venue that states a start
        now keeps it, and a venue that does not takes the volume's.
        """
        super().populate(competition, volume)
        self.adopt(
            venue=ContextVenue(self.root, competition, volume, venue),
            i18n=ContextI18nGlobal(self.root, competition)
        ).add(language=i18n.languages[self.data['venue']['language']].as_dict())

        # In place, and nothing beside it: the composed schema is checked *after* this runs, and
        # a derived `start_utc` left in the data fails it as `Wrong key`. What the meta said is
        # in the meta; what a template needs is the clock.
        self.data['venue']['start'] = local_minutes(
            self.data['venue'].get('start', self.data['volume']['start']),
            self.data['volume']['date'], self.data['venue']['timezone'])
