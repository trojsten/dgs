import abc
from pathlib import Path

from enschema import Schema

from core import i18n
from core.builder.context.buildable import BuildableFileSystemTreeContext
from core.builder.context.module import ContextModule
from core.i18n import Locale
from renderer import ConstantsContext
from .validators import NabojValidator
from .base import ContextNaboj
from .hierarchy import ContextCompetition, ContextVolume, ContextLanguage, ContextVenue
from .i18n import ContextI18nGlobal, ContextI18n


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
            venue=ContextVenue(self.root, competition, volume, venue)
                               .override('start', self.data['volume']['start']),
            i18n=ContextI18nGlobal(self.root, competition)
        ).add(language=i18n.languages[self.data['venue']['language']].as_dict())

        if 'start' not in self.data['venue']:
            self.data['venue']['start'] = self.data['volume']['start']
