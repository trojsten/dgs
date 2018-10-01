#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from build import *
from colorama import Fore, Style

args = modifyParserHandout(createDefaultParser()).parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = buildHandoutContext(launchDirectory, args.course, args.year, args.lesson)
if args.debug:
    pprint.pprint(context)

print(Fore.CYAN + Style.DIM + "Invoking template builder on {course}/{year}/{lesson}".format(
    course  = args.course,
    year    = args.year,
    lesson  = args.lesson,
) + Style.RESET_ALL)

buildFormatTemplate(thisDirectory, 'format-handout.tex'.format(build = build), context, outputDirectory)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)
