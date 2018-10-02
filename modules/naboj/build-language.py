#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from colorama import Fore, Style

import build, core.builder
from core.utils import *

args = build.createNabojParser('language').parse_args()

competitionId       = args.competition
volumeId            = '{:02d}'.format(args.volume)
languageId          = args.language
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print("{} {}".format(
    colour("Invoking Náboj template builder on", 'act'),
    colour(build.nodePathNaboj(launchDirectory, competitionId, volumeId), 'path'),
))

bookletContext = build.bookletContext(launchDirectory, competitionId, volumeId, languageId)
if args.debug:
    pprint.pprint(bookletContext)

for template in ['booklet.tex', 'answers.tex', 'answers-mod5.tex', 'constants.tex', 'cover.tex', 'instructions.tex']:
    core.builder.jinjaTemplate(os.path.join(thisDirectory, 'templates'), template, bookletContext, outputDirectory)

for template in ['format.tex']:
    core.builder.jinjaTemplate(thisDirectory, template, bookletContext, outputDirectory)

for template in ['intro.tex', 'instructions-text.tex']:
    core.builder.jinjaTemplate(os.path.join(launchDirectory, competitionId, '{:02d}'.format(args.volume), 'languages', args.language), template, bookletContext, outputDirectory)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

