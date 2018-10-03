#!/usr/bin/env python3

import argparse, os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

def createNabojParser(target):
    parser = argparser.createGenericParser()
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
    return context.mergeDicts(context.loadYaml(root, competition, 'meta.yaml'), {
        'id': competition,
    })

def volumeContext(root, competition, volume):
    vol = context.loadMeta(nodePathNaboj, (root, competition, volume))
    vol['problems'] = context.addNumbers(vol['problems'], 1)
    vol['problemsMod'] = context.splitMod(vol['problems'], 5, 1)
    return context.mergeDicts(vol, {
        'id': volume,
        'number': int(volume),
    })

def languageContext(language):
    return {
        'id': language,
    }

def venueContext(root, competition, volume, venue):
    try:
        venueMeta = context.loadYaml(root, competition, volume, 'venues', venue, 'meta.yaml')
        return context.mergeDicts(venueMeta, {
            'id':       venue,
            'teams3':   context.splitDiv(context.numerate(venueMeta['teams']), 3),
        })
    except KeyError as e:
        print(c.err("[FATAL] KeyError {}".format(e)))
        
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
