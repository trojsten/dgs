#!/usr/bin/python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import *
from colorama import Fore, Style

def buildModuleContext():
    return {
        'id': 'naboj',
    }

def buildSeminarContext(root, seminar):
    return mergeDicts(loadYaml(root, seminar, 'meta.yaml'), {
        'id': seminar,
    })

def buildVolumeContext(root, seminar, volume):
    vol = loadYaml(root, seminar, volume, 'languages', 'meta.yaml')
    vol['problems'] = addNumbers(vol['problems'], 1)
    vol['problemsMod'] = splitMod(vol['problems'], 5, 1)
    return mergeDicts(vol, {
        'id': volume,
        'number': int(volume),
    })

def buildLanguageContext(language):
    return {
        'id': language,
    }

def buildVenueContext(root, seminar, volume, venue):
    try:
        venueMeta = loadYaml(root, seminar, volume, 'venues', venue, 'meta.yaml')
        return mergeDicts(venueMeta, {
            'id':       venue,
            'teams3':   splitDiv(numerate(venueMeta['teams']), 3),
        })
    except KeyError as e:
        print(Fore.RED + "[FATAL] KeyError {}".format(e) + Style.RESET_ALL)
        
def buildBookletContext(root, seminar, volume, language):
    return {
        'i18n':             buildI18nContext        (root, seminar, volume, language),
        'module':           buildModuleContext(),
        'seminar':          buildSeminarContext     (root, seminar),
        'volume':           buildVolumeContext      (root, seminar, volume),
        'language':         buildLanguageContext    (language),
    }

def buildTearoffContext(root, seminar, volume, venue):
    return {
        'i18n':             buildGlobalI18nContext(),
        'module':           buildModuleContext(),
        'seminar':          buildSeminarContext     (root, seminar),
        'volume':           buildVolumeContext      (root, seminar, volume),
        'venue':            buildVenueContext       (root, seminar, volume, venue),
    }

def buildI18nContext(moduleRoot, seminar, volume, language):
    return loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')

def buildGlobalI18nContext():
    context = {}
    for language in ['slovak', 'czech', 'hungarian', 'polish', 'english']:
        context[language] = loadYaml(os.path.dirname(os.path.realpath(__file__)), 'templates', 'i18n', language + '.yaml')
    return context
