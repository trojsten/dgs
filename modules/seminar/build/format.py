import os, sys, pprint

import base
import core.utilities.jinja as jinja
import core.utilities.colour as c

class BuilderFormat(base.BuilderSeminar):
    def __init__(self):
        super().__init__(
            base.ContextHandout,
            formatters      = ['format-handout.tex'],
            templates       = ['handout.tex'],
            templateRoot    = os.path.dirname(os.path.dirname(__file__)),
        )
        self.target = 'handout'

builder = BuilderHandout()
args = build.createSeminarParser().parse_args()

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

context = build.ContextBooklet(launchDirectory, args.competition, args.volume, args.semester, args.round)

print(c.act("Invoking formatting template builder on {target:<12}".format(target = target)),
    c.path("seminar{competition}{volume}{semester}{round}".format(
        target      = target,
        competition = '' if args.competition    is None else '/{}'.format(args.competition),
        volume      = '' if args.volume         is None else '/{}'.format(args.volume),
        semester    = '' if args.semester       is None else '/{}'.format(args.semester),
        round       = '' if args.round          is None else '/{}'.format(args.round),
    ))
)

if args.debug:
    context.print()

jinja.printTemplate(thisDirectory, 'format-{target}.tex'.format(target = target), context.data, outputDirectory)

print(c.ok("Template builder successful"))
