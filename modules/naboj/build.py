#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from colorama import Fore, Style

sys.path.append('.')

import core.builder
from core.utils import *

def createNabojParser(target):
    parser = core.builder.createGenericParser()
    parser.add_argument('competition', choices = ['FKS', 'KMS'])
    parser.add_argument('volume',      type = int)
    if target == 'language':
        parser.add_argument('language', type = str)
    elif target == 'venue':
        parser.add_argument('venue',    type = str)
    else:
        raise KeyError("Unknown Náboj parser target {}".format(target))

    return parser

def nodePathNaboj(root, competition = None, volume = None):
    return os.path.join(
        root,
        '' if competition is None else  competition,
        '' if volume is None else       volume,
    )

def moduleContext():
    return {
        'id': 'naboj',
    }

def competitionContext(root, competition):
    return mergeDicts(loadYaml(root, competition, 'meta.yaml'), {
        'id': competition,
    })

def volumeContext(root, competition, volume):
    vol = loadMeta(nodePathNaboj, (root, competition, volume))
    vol['problems'] = addNumbers(vol['problems'], 1)
    vol['problemsMod'] = splitMod(vol['problems'], 5, 1)
    return mergeDicts(vol, {
        'id': volume,
        'number': int(volume),
    })

def languageContext(language):
    return {
        'id': language,
    }

def venueContext(root, competition, volume, venue):
    try:
        venueMeta = loadYaml(root, competition, volume, 'venues', venue, 'meta.yaml')
        return mergeDicts(venueMeta, {
            'id':       venue,
            'teams3':   splitDiv(numerate(venueMeta['teams']), 3),
        })
    except KeyError as e:
        print(Fore.RED + "[FATAL] KeyError {}".format(e) + Style.RESET_ALL)
        
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
    return loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')

def globalI18nContext():
    context = {}
    for language in ['slovak', 'czech', 'hungarian', 'polish', 'english', 'russian']:
        context[language] = loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')
    return context
