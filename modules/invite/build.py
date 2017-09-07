import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import jinjaEnv, mergeInto, renderList, readableDir
from colorama import Fore, Style

def getSemesterMetadata(root, seminar, volume, semester):
    try:
        seminarMeta         = yaml.load(open(os.path.join(root, seminarId, 'meta.yaml'), 'r'))
        volumeMeta          = yaml.load(open(os.path.join(root, seminarId, volumeId, 'meta.yaml'), 'r'))
        semesterMeta        = yaml.load(open(os.path.join(root, seminarId, volumeId, semesterId, 'meta.yaml'), 'r'))
        campMeta            = yaml.load(open(os.path.join(root, seminarId, volumeId, semesterId, 'camp.yaml'), 'r'))
        childrenMeta        = yaml.load(open(os.path.join(root, seminarId, volumeId, semesterId, 'children.yaml'), 'r'))

        context = {
            'seminar': seminarMeta,
            'semester': semesterMeta,
            'camp': campMeta,
        }
        mergeInto(context, childrenMeta) 
        update = {
            'seminar': {
                'id':           args.seminar,
            },
            'volume': {
                'id':           '{:02d}'.format(args.volume),
                'number':       args.volume
            },
            'semester': {
                'id':           str(args.semester),
                'number':       args.semester,
                'nominative':   ['zimná', 'letná'][args.semester - 1],
                'nominativeNeuter': ['zimné', 'letné'][args.semester - 1],
                'genitive':     ['zimnej', 'letnej'][args.semester - 1],
            },
        }

        return mergeInto(context, update)
    
    except FileNotFoundError as e:
        print(Fore.RED + "[FATAL] {}".format(e) + Style.RESET_ALL)
        sys.exit(-1)
    
parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ invite from repository",
)
parser.add_argument('launch',           action = readableDir) 
parser.add_argument('seminar',          choices = ['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX'])
parser.add_argument('volume',           type = int)
parser.add_argument('semester',         type = int, choices = [1, 2])
parser.add_argument('-o', '--output',   action = readableDir) 
parser.add_argument('-v', '--verbose',  action = 'store_true')
args = parser.parse_args()

seminarId           = '{}'.format(args.seminar)
volumeId            = '{:02d}'.format(args.volume)
semesterId          = '{}'.format(args.semester)
launchDirectory     = os.path.realpath(args.launch)
thisDirectory       = os.path.realpath(os.path.dirname(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print(Fore.CYAN + Style.DIM + "Invoking invite template builder on {}".format(os.path.realpath(os.path.join(launchDirectory, seminarId, volumeId, semesterId))) + Style.RESET_ALL)

print(outputDirectory)
context = getSemesterMetadata(launchDirectory, seminarId, volumeId, semesterId)

if (args.verbose):
    pprint.pprint(context)

for template in ['invite.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(context), file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['invite.sty']:
    print(jinjaEnv(os.path.join(thisDirectory, '.')).get_template(template).render(context), file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)


