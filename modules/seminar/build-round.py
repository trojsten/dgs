#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

args = build.createSeminarParser().parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = build.ContextBooklet(launchDirectory, args.competition, args.volume, args.semester, args.round)

print(c.act("Invoking round template builder on round "), c.path("seminar/{competition}/{volume}/{semester}/{round}".format(
        competition = args.competition,
        volume      = args.volume,
        semester    = args.semester,
        round       = args.round,
    ))
)

if args.debug:
    context.print()

for template in ['problems.tex', 'solutions.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), template, context.data, outputDirectory)

print(c.ok("Template builder successful"))

