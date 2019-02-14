#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from build import *
from colorama import Fore, Style

args = createParser(3).parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = buildInviteContext(launchDirectory, args.competition, args.volume, args.semester)
if args.verbose:
    pprint.pprint(context)

print(Fore.CYAN + Style.DIM + "Invoking template builder on invite '{competition}/{volume}/{semester}'".format(
    competition = args.competition,
    volume      = args.volume,
    semester    = args.semester,
) + Style.RESET_ALL)

for template in ['invite.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(context),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['intro.tex', 'rules.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'styles', args.competition, 'templates')).get_template(template).render(context),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

