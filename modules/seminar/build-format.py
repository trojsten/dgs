#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from colorama import Fore, Style

sys.path.append('.')
import build, core.builder

args = build.createSeminarParser().parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

if args.competition is None:
    target = 'root'
    args.volume = args.semester = args.round = None
elif args.volume is None:
    target = 'competition'
    args.semester = args.round = None
elif args.semester is None:
    target = 'volume'
    args.round = None
elif args.round is None:
    target = 'semester'
else:
    target = 'round'

context = build.bookletContext(launchDirectory, args.competition, args.volume, args.semester, args.round)
if args.debug:
    pprint.pprint(context)

print(Fore.CYAN + Style.DIM + "Invoking template builder on {target} 'seminar{competition}{volume}{semester}{round}'".format(
    target      = target,
    competition = '' if args.competition    is None else '/{}'.format(args.competition),
    volume      = '' if args.volume         is None else '/{}'.format(args.volume),
    semester    = '' if args.semester       is None else '/{}'.format(args.semester),
    round       = '' if args.round          is None else '/{}'.format(args.round),
) + Style.RESET_ALL)

core.builder.jinjaTemplate(thisDirectory, 'format-{target}.tex'.format(target = target), context, outputDirectory)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)
