#!/usr/bin/env python3

import os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

args = build.createNabojParser('language').parse_args()

competitionId       = args.competition
volumeId            = '{:02d}'.format(args.volume)
languageId          = args.language
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print(c.act("Invoking Náboj template builder on"), c.path(build.nodePathNaboj(launchDirectory, competitionId, volumeId)))

bookletContext = build.bookletContext(launchDirectory, competitionId, volumeId, languageId)
if args.debug:
    pprint.pprint(bookletContext)

for template in ['booklet.tex', 'answers.tex', 'answers-mod5.tex', 'constants.tex', 'cover.tex', 'instructions.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), template, bookletContext, outputDirectory)

for template in ['format.tex']:
    jinja.printTemplate(thisDirectory, template, bookletContext, outputDirectory)

for template in ['intro.tex', 'instructions-text.tex']:
    jinja.printTemplate(os.path.join(launchDirectory, competitionId, '{:02d}'.format(args.volume), 'languages', args.language), template, bookletContext, outputDirectory)

print(c.ok("Template builder successful"))

