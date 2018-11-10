import os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c

args = build.createNabojLanguageParser().parse_args()

launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

context = build.ContextBooklet(launchDirectory, args.competition, args.volume, args.language)

print(c.act("Invoking Náboj template builder on"), c.path("{competition}/{volume}/{language}".format(
        competition = args.competition,
        volume      = args.volume,
        language    = args.language,
    ))
)

if args.debug:
    context.print()

for template in ['booklet.tex', 'answers.tex', 'answers-mod5.tex', 'constants.tex', 'cover.tex', 'instructions.tex']:
    jinja.printTemplate(os.path.join(thisDirectory, 'templates'), template, context.data, outputDirectory)

for template in ['format.tex']:
    jinja.printTemplate(thisDirectory, template, context.data, outputDirectory)

for template in ['intro.tex', 'instructions-text.tex']:
    jinja.printTemplate(os.path.join(launchDirectory, args.competition, '{:02d}'.format(args.volume), 'languages', args.language), template, context.data, outputDirectory)

print(c.ok("Template builder successful"))

