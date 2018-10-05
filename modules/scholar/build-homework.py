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

context             = build.ContextHomework(launchDirectory, args.course, args.year, args.issue)

if args.debug:
    context.print()    

print(c.act("Invoking template builder on homework"), c.path("{course}/{year}/{issue}".format(
        course  = args.course,
        year    = args.year,
        issue   = args.issue,
    ))
)

for template in ['format-homework.tex']:
    jinja.printTemplate(thisDirectory, template, context.data, outputDirectory)

for template in ['homework.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), template, context.data, outputDirectory)

print(c.ok("Template builder successful"))
