#!/usr/bin/python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import jinjaEnv, mergeInto, renderList, readableDir
from colorama import Fore, Style

def getRoundMetadata(root, seminar, volume, semester, round):
    try:
        seminarMeta         = yaml.load(open(os.path.join(root, seminarId, 'meta.yaml'), 'r'))
        volumeMeta          = yaml.load(open(os.path.join(root, seminarId, volumeId, 'meta.yaml'), 'r'))
        semesterMeta        = yaml.load(open(os.path.join(root, seminarId, volumeId, semesterId, 'meta.yaml'), 'r'))
        roundMeta           = yaml.load(open(os.path.join(root, seminarId, volumeId, semesterId, roundId, 'meta.yaml'), 'r'))
        roundDirectory      = os.path.join(root, seminarId, volumeId, semesterId, roundId)

        problemsMetas       = []

        for name in sorted(os.listdir(roundDirectory)):
            if not os.path.isdir(os.path.join(roundDirectory, name)):
                continue
            if not os.path.isfile(os.path.join(roundDirectory, name, 'meta.yaml')):
                raise FileNotFoundError("Directory '{}' is present but there is no 'meta.yaml' in it".format(name))
    
            problemMeta = yaml.load(open(os.path.join(roundDirectory, name, 'meta.yaml')))
            problemMeta['id'] = name
            problemMeta['number'] = int(name)
            problemMeta['solutionBy'] = problemMeta['solutionBy']
            problemMeta['evaluation'] = problemMeta['evaluation']
            problemMeta['categories'] = seminarMeta['categories'][int(name) - 1]
            problemsMetas.append(problemMeta)
            
        context = {
            'seminar': seminarMeta,
            'semester': semesterMeta,
            'round': roundMeta,
        }
        update = {
            'seminar': {
                'id':           args.seminar,
            },
            'volume': {
                'id':           '{:02d}'.format(args.volume),
                'number':       args.volume
            },
            'semester': {
                'id':           str(args.semester),
                'number':       args.semester,
                'nominative':   ['zimná', 'letná'][args.semester - 1],
                'genitive':     ['zimnej', 'letnej'][args.semester - 1],
            },
            'round': {
                'id':           str(args.round),
                'number':       args.round,
                'problems':     problemsMetas,
            },
        }

        return mergeInto(context, update)
    
    except FileNotFoundError as e:
        print(Fore.RED + "[FATAL] {}".format(e) + Style.RESET_ALL)
        sys.exit(-1)
    
parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ round from repository",
)
parser.add_argument('launch',           action = readableDir) 
parser.add_argument('seminar',          choices = ['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX'])
parser.add_argument('volume',           type = int)
parser.add_argument('semester',         type = int, choices = [1, 2])
parser.add_argument('round',            type = int, choices = [1, 2, 3])
parser.add_argument('-o', '--output',   action = readableDir) 
parser.add_argument('-v', '--verbose',  action = 'store_true')
args = parser.parse_args()

seminarId           = '{}'.format(args.seminar)
volumeId            = '{:02d}'.format(args.volume)
semesterId          = '{}'.format(args.semester)
roundId             = '{}'.format(args.round)
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print(Fore.CYAN + Style.DIM + "Invoking seminar template builder on {}".format(os.path.realpath(os.path.join(launchDirectory, seminarId, volumeId, semesterId, roundId))) + Style.RESET_ALL)
context = getRoundMetadata(launchDirectory, seminarId, volumeId, semesterId, roundId)

if (args.verbose):
    pprint.pprint(context)

for template in ['problems.tex', 'solutions.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(context), file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['seminar.sty']:
    print(jinjaEnv(os.path.join(thisDirectory, '.')).get_template(template).render(context), file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)


