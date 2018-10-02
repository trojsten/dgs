#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from colorama import Fore, Style

import build, core.builder

args = build.createNabojParser('venue').parse_args()

competitionId       = args.competition
volumeId            = '{:02d}'.format(args.volume)
venueId             = args.venue
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print(Fore.CYAN + Style.DIM + "Invoking Náboj template builder on {}".format(build.nodePathNaboj(launchDirectory, competitionId, volumeId)) + Style.RESET_ALL)

tearoffContext = build.tearoffContext(launchDirectory, competitionId, volumeId, venueId)
if args.debug:
    pprint.pprint(tearoffContext)

for target in ['barcodes.txt', 'tearoff.tex']:
    core.builder.jinjaTemplate(os.path.join(thisDirectory, 'templates'), target, tearoffContext, outputDirectory)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)
