import argparse
import os
import sys
import pprint

sys.path.append('.')

from core.utilities import jinja, dicts, colour as c, argparser, context

class BuilderNaboj(context.BaseBuilder):
    module = 'naboj'

    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('-c', '--competition',  choices = ['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
        self.parser.add_argument('-v', '--volume',       type = int)
    

class ContextI18n(context.Context):
    def __init__(self, language):
        super().__init__()
        self.loadYaml(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'templates', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.Context):
    def __init__(self):
        super().__init__()
        for language in ['slovak', 'czech', 'hungarian', 'polish', 'english', 'russian']:
            self.absorb(language, ContextI18n(language))


class ContextNaboj(context.Context):
    def nodePath(self, root, competition = None, volume = None, targetType = None, target = None):
        return os.path.join(
            root,
            '' if competition   is None else    competition,
            '' if volume        is None else    '{:02d}'.format(volume),
            '' if targetType    is None else    targetType,
            '' if target        is None else    target,
        )


class ContextModule(ContextNaboj):
    def __init__(self, module):
        super().__init__()
        self.addId(module)


class ContextCompetition(ContextNaboj):
    def __init__(self, root, competition):
        super().__init__()
        self.loadMeta(root, competition) \
            .addId(competition)

        
class ContextVolume(ContextNaboj):
    def __init__(self, root, competition, volume):
        super().__init__()
        self.id = '{:02d}'.format(volume)
        self.loadMeta(root, competition, volume) \
            .addId(self.id) \
            .addNumber(volume)

        self.add({'problems':       context.addNumbers(self.data['problems'], 1)})
        self.add({'problemsMod5':   context.splitMod(self.data['problems'], 5, 1)})

        self.data['problems'].append({'id': '-end-', 'number': 0})

class ContextLanguage(ContextNaboj):
    def __init__(self, language):
        super().__init__()
        self.addId(language)


class ContextVenue(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.loadMeta(root, competition, volume, 'venues', venue).addId(venue)
        self.add({'teamsDiv3':      context.splitDiv(context.numerate(self.data.get('teams')), 3)})


class ContextBooklet(ContextNaboj):
    def __init__(self, root, competition, volume, language):
        super().__init__()
        self.loadMeta(root, competition, volume, 'languages', language)
        self.absorb('module',           ContextModule       ('naboj'))
        self.absorb('competition',      ContextCompetition  (root, competition))
        self.absorb('volume',           ContextVolume       (root, competition, volume))
        self.absorb('language',         ContextLanguage     (language))
        self.absorb('i18n',             ContextI18n         (language))


class ContextTearoff(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.absorb('module',           ContextModule       ('naboj'))
        self.absorb('competition',      ContextCompetition  (root, competition))
        self.absorb('volume',           ContextVolume       (root, competition, volume))
        self.absorb('venue',            ContextVenue        (root, competition, volume, venue))
        self.absorb('i18n',             ContextI18nGlobal   ())
