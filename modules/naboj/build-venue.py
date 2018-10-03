#!/usr/bin/env python3

import os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

args = build.createNabojParser('venue').parse_args()

competitionId       = args.competition
volumeId            = '{:02d}'.format(args.volume)
venueId             = args.venue
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print(c.act("Invoking Náboj template builder on"), c.path(build.nodePathNaboj(launchDirectory, competitionId, volumeId)))

tearoffContext = build.tearoffContext(launchDirectory, competitionId, volumeId, venueId)
if args.debug:
    pprint.pprint(tearoffContext)

for target in ['barcodes.txt', 'tearoff.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), target, tearoffContext, outputDirectory)

print(c.ok("Template builder successful"))
