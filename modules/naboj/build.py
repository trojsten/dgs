import argparse, os, sys, pprint

sys.path.append('.')
import core.utilities.jinja as jinja
import core.utilities.dicts as dicts
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

def createNabojParser():
    parser = argparser.createGenericParser()
    parser.add_argument('-c', '--competition',  choices = ['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
    parser.add_argument('-v', '--volume',       type = int)
    return parser

def createNabojLanguageParser():
    parser = createNabojParser()
    parser.add_argument('-l', '--language',     type = str)
    return parser

def createNabojVenueParser():
    parser = createNabojParser()
    parser.add_argument('-p', '--venue',        type = str)
    return parser

class ContextI18n(context.Context):
    def __init__(self, language):
        super().__init__()
        self.loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')
        

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

class ContextLanguage(ContextNaboj):
    def __init__(self, language):
        super().__init__()
        self.addId(language)


class ContextVenue(ContextNaboj):
    def __init__(self, root, competition, volume, venue):
        super().__init__()
        self.loadMeta(root, competition, volume, 'venues', venue).addId(venue)
        
        self.add('teamsDiv3', context.splidDiv(context.numerate(self.get('teams')), 3))

class ContextBooklet(ContextNaboj):
    def __init__(self, root, competition, volume, language):
        super().__init__()
        self.absorb('module',           ContextModule       ('naboj'))
        self.absorb('competition',      ContextCompetition  (root, competition))
        self.absorb('volume',           ContextVolume       (root, competition, volume))
        self.absorb('language',         ContextLanguage     (language))
        self.absorb('i18n',             ContextI18n         (language))

 

def bookletContext(root, competition, volume, language):
    return {
        'module':           moduleContext      (),
        'competition':      competitionContext (root, competition),
        'volume':           volumeContext      (root, competition, volume),
        'i18n':             i18nContext        (root, competition, volume, language),
        'language':         languageContext    (language),
    }

def tearoffContext(root, competition, volume, venue):
    return {
        'i18n':             globalI18nContext  (),
        'module':           moduleContext      (),
        'competition':      competitionContext (root, competition),
        'volume':           volumeContext      (root, competition, volume),
        'venue':            venueContext       (root, competition, volume, venue),
    }

def i18nContext(moduleRoot, competition, volume, language):
    return context.loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')

def globalI18nContext():
    i18n = {}
    for language in ['slovak', 'czech', 'hungarian', 'polish', 'english', 'russian']:
        i18n[language] = context.loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')
    return i18n
