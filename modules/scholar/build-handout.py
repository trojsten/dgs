#!/usr/bin/env python3

import argparse, os, sys, pprint

sys.path.append('.')
import build, core.builder
from core.utils import *

args = build.createScholarParser('handout').parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = build.handoutContext(launchDirectory, args.course, args.year, args.lesson)
if args.debug:
    pprint.pprint(context)

print("{}{}{}".format(
    colour("Invoking template builder on handout '", 'act'),
    colour("{course}/{year}/{lesson}".format(
        course  = args.course,
        year    = args.year,
        lesson  = args.lesson,
    ), 'path'),
    colour("'", 'act')
))

for template in ['handout.tex']:
    core.builder.jinjaTemplate(os.path.join(thisDirectory, 'templates'), template, context, outputDirectory)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)
