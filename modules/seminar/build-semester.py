#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from build import *
from colorama import Fore, Style

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ competition round booklet from repository",
)
parser.add_argument('launch',           action = readableDir) 
parser.add_argument('competition',      choices = ['FKS', 'KMS', 'UFO', 'KSP', 'Prask'])
parser.add_argument('volume',           type = int)
parser.add_argument('semester',         type = int)
parser.add_argument('-o', '--output',   action = readableDir) 
parser.add_argument('-v', '--verbose',  action = 'store_true')
args = parser.parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = buildSemesterBookletContext(launchDirectory, args.competition, args.volume, args.semester)
pprint.pprint(context)

print(Fore.CYAN + Style.DIM + "Invoking template builder on semester {competition}/{volume}/{semester}".format(
    competition = args.competition,
    volume      = args.volume,
    semester    = args.semester,
) + Style.RESET_ALL)

for template in ['semester.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(context),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

