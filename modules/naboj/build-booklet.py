#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from build import *
from colorama import Fore, Style

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ Náboj booklet from repository",
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

for template in ['format.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, '.')).get_template(template).render(buildBookletContext(launchDirectory, seminarId, volumeId, languageId)),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

