#!/usr/bin/python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import jinjaEnv, mergeDict, mergeDicts, renderList, readableDir, splitDiv, splitMod, loadYaml, addNumbers
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
    vol = loadYaml(root, seminar, volume, 'meta.yaml')
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
        volumeMeta              = loadYaml(root, seminar, volume, 'meta.yaml')
        venueMeta               = volumeMeta['venues'][venue]
    except KeyError as e:
        print(Fore.RED + "[FATAL] KeyError {}".format(e) + Style.RESET_ALL)

    return {
        'id':       venue,
        'name':     venueMeta['name'],
        'teams3':   splitDiv(venueMeta['teams'], 3),
    }
    
def buildBookletContext(root, seminar, volume, language):
    return {
        'i18n':             buildI18nContext(root, seminar, volume, language),
        'module':           buildModuleContext(),
        'seminar':          buildSeminarContext(root, seminar),
        'volume':           buildVolumeContext(root, seminar, volume),
        'language':         buildLanguageContext(language),
    }

def buildTearoffContext(root, seminar, volume, venue):
    return {
        'i18n':             buildGlobalI18nContext(root, seminar, volume),
        'module':           buildModuleContext(),
        'seminar':          buildSeminarContext(root, seminar),
        'volume':           buildVolumeContext(root, seminar, volume),
        'venue':            buildVenueContext(root, seminar, volume, venue),
    }
    
def buildI18nContext(root, seminar, volume, language):
    try:
        return loadYaml(thisDirectory, 'templates', 'i18n', language + '.yaml')
    except FileNotFoundError as e:
        print(Fore.RED + "[FATAL] {}".format(e) + Style.RESET_ALL)
        return None

def buildGlobalI18nContext(root, seminar, volume):
    context = {}
    for language in ['slovak', 'czech', 'hungarian', 'polish', 'english']:
        context[language] = loadYaml(thisDirectory, 'templates', 'i18n', language + '.yaml')
    return context

def getVolumeMetadata(root, seminar, volume, language):
    try:
        seminarMeta         = yaml.load(open(os.path.join(root, seminar, 'meta.yaml'), 'r'))
        volumeMeta          = yaml.load(open(os.path.join(root, seminar, volume, 'meta.yaml'), 'r'))
        languageMeta        = yaml.load(open(os.path.join(root, seminar, volume, language, 'meta.yaml'), 'r'))

        problemMetas        = []
        problemNum          = 1
        for problem in volumeMeta['problems']:
            problemMeta = {
                'number':   problemNum,
                'id':       problem,
            }
            problemNum += 1
            problemMetas.append(problemMeta)
        
        context = {
            'seminar': seminarMeta,
        }
        update = {
            'I18n': buildI18n(root, seminar, volume, language),
            'module': {
                'id':           'naboj',
            },
            'seminar': {
                'id':           args.seminar,
            },
            'volume': {
                'id':           '{:02d}'.format(args.volume),
                'number':       args.volume,
                'problems':     problemMetas,
                'problemsMod':  splitMod(problemMetas, 5, 1),
            },
            'language': {
                'id':           args.language,
            },
        }
        return mergeDicts(context, update)
    
    except FileNotFoundError as e:
        print(Fore.RED + "[FATAL] {}".format(e) + Style.RESET_ALL)
        sys.exit(-1)
    
parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ Náboj volume from repository",
)
parser.add_argument('launch',           action = readableDir) 
parser.add_argument('seminar',          choices = ['FKS', 'KMS'])
parser.add_argument('volume',           type = int)
parser.add_argument('language',         choices = ['slovak', 'czech', 'english', 'polish', 'hungarian'])
parser.add_argument('-o', '--output',   action = readableDir) 
parser.add_argument('-v', '--verbose',  action = 'store_true')
args = parser.parse_args()

seminarId           = args.seminar
volumeId            = '{:02d}'.format(args.volume)
languageId          = args.language
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

pprint.pprint(buildBookletContext(launchDirectory, seminarId, volumeId, languageId))

print(Fore.CYAN + Style.DIM + "Invoking Náboj template builder on {}".format(os.path.realpath(os.path.join(launchDirectory, seminarId, volumeId)) + Style.RESET_ALL))

for template in ['booklet.tex', 'answers.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(buildBookletContext(launchDirectory, seminarId, volumeId, languageId)),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['tearoff.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(buildTearoffContext(launchDirectory, seminarId, volumeId, 'kosice')),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['format.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, '.')).get_template(template).render(buildBookletContext(launchDirectory, seminarId, volumeId, languageId)),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

