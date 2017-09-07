import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import *
from colorama import Fore, Style

def buildModuleContext():
    return {
        'id': 'naboj',
    }

def buildCompetitionContext(root, competition):
    return mergeDicts(loadYaml(root, competition, 'meta.yaml'), {
        'id': competition,
    })

def buildVolumeContext(root, competition, volume):
    vol = loadYaml(root, competition, volume, 'languages', 'meta.yaml')
    date = loadYaml(root, competition, volume, 'meta.yaml')
    vol['problems'] = addNumbers(vol['problems'], 1)
    vol['problemsMod'] = splitMod(vol['problems'], 5, 1)
    return mergeDicts(vol, date, {
        'id': volume,
        'number': int(volume),
    })

def buildLanguageContext(language):
    return {
        'id': language,
    }

def buildVenueContext(root, competition, volume, venue):
    try:
        venueMeta = loadYaml(root, competition, volume, 'venues', venue, 'meta.yaml')
        return mergeDicts(venueMeta, {
            'id':       venue,
            'teams3':   splitDiv(numerate(venueMeta['teams']), 3),
        })
    except KeyError as e:
        print(Fore.RED + "[FATAL] KeyError {}".format(e) + Style.RESET_ALL)
        
def buildBookletContext(root, competition, volume, language):
    return {
        'i18n':             buildI18nContext        (root, competition, volume, language),
        'module':           buildModuleContext      (),
        'competition':      buildCompetitionContext (root, competition),
        'volume':           buildVolumeContext      (root, competition, volume),
        'language':         buildLanguageContext    (language),
    }

def buildTearoffContext(root, competition, volume, venue):
    return {
        'i18n':             buildGlobalI18nContext  (),
        'module':           buildModuleContext      (),
        'competition':      buildCompetitionContext (root, competition),
        'volume':           buildVolumeContext      (root, competition, volume),
        'venue':            buildVenueContext       (root, competition, volume, venue),
    }

def buildI18nContext(moduleRoot, competition, volume, language):
    return loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')

def buildGlobalI18nContext():
    context = {}
    for language in ['slovak', 'czech', 'hungarian', 'polish', 'english']:
        context[language] = loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')
    return context
