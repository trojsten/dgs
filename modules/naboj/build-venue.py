import os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c

args = build.createNabojVenueParser().parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = build.ContextTearoff(launchDirectory, args.competition, args.volume, args.venue)

print(c.act("Invoking Náboj template builder on"), c.path("{competition}/{volume}/{venue}".format(
        competition = args.competition,
        volume      = args.volume,
        venue       = args.venue,
    ))
)

if args.debug:
    context.print()

for target in ['barcodes.txt', 'tearoff.tex', 'envelope.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), target, context.data, outputDirectory)

print(c.ok("Template builder successful"))
