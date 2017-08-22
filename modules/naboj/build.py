#!/usr/bin/python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import jinjaEnv, mergeInto, renderList, readableDir
from colorama import Fore, Style

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
            },
            'language': {
                'id':           args.language,
            },
        }
        return mergeInto(context, update)
    
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

print(Fore.CYAN + Style.DIM + "Invoking Náboj template builder on {}".format(os.path.realpath(os.path.join(launchDirectory, seminarId, volumeId)) + Style.RESET_ALL))
context = getVolumeMetadata(launchDirectory, seminarId, volumeId, languageId)

if (args.verbose):
    pprint.pprint(context)

#for template in ['booklet.tex', 'tearoff.tex', 'answers.tex']:
for template in ['booklet.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(context), file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['format.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, '.')).get_template(template).render(context), file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

