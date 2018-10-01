#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from colorama import Fore, Style

sys.path.append('.')
import build, core.builder

args = build.createSeminarParser().parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = build.bookletContext(launchDirectory, args.competition, args.volume, args.semester, args.round)

if args.debug:
    pprint.pprint(context)

print(Fore.CYAN + Style.DIM + "Invoking template builder on round '{competition}/{volume}/{semester}/{round}'".format(
    competition = args.competition,
    volume      = args.volume,
    semester    = args.semester,
    round       = args.round,
) + Style.RESET_ALL)

for template in ['problems.tex', 'solutions.tex']:
    core.builder.jinjaTemplate(os.path.join(thisDirectory, 'templates'), template, context, outputDirectory)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

