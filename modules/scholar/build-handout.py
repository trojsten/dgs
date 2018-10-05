#!/usr/bin/env python3

import os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c

args = build.createScholarParser().parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context             = build.ContextHandout(launchDirectory, args.course, args.year, args.issue)

if args.debug:
    context.print()

print(c.act("Invoking template builder on handout"), c.path("{course}/{year}/{lesson}".format(
        course  = args.course,
        year    = args.year,
        lesson  = args.issue,
    ))
)

for template in ['format-handout.tex']:
    jinja.printTemplate(thisDirectory, template, context.data, outputDirectory)

for template in ['handout.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), template, context.data, outputDirectory)

print(c.ok("Template builder successful"))
