import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import readableDir, jinjaEnv
from build import buildTearoffContext
from colorama import Fore, Style

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ Náboj venue-specific documents from repository",
)
parser.add_argument('launch',           action = readableDir) 
parser.add_argument('seminar',          choices = ['FKS', 'KMS'])
parser.add_argument('volume',           type = int)
parser.add_argument('venue',            type = str)
parser.add_argument('-o', '--output',   action = readableDir) 
parser.add_argument('-v', '--verbose',  action = 'store_true')
args = parser.parse_args()

seminarId           = args.seminar
volumeId            = '{:02d}'.format(args.volume)
venueId             = args.venue
root                = os.path.realpath(args.launch)
thisDirectory       = os.path.dirname(os.path.realpath(__file__))
outputDirectory     = os.path.realpath(args.output) if args.output else None

print(Fore.CYAN + Style.DIM + "Invoking Náboj template builder on {}".format(os.path.realpath(os.path.join(root, seminarId, volumeId)) + Style.RESET_ALL))
print(
    jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template('barcodes.txt').render(
        buildTearoffContext(root, seminarId, volumeId, venueId)
    ),
    file = open(os.path.join(outputDirectory, 'barcodes.txt'), 'w') if outputDirectory else sys.stdout
)
print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)
