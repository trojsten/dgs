#!/usr/bin/env python3

import re, argparse, sys, json
from ruamel import yaml

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ Náboj barcodes for a venue from repository",
)
parser.add_argument('name',     type = str)
parser.add_argument('number',   type = int)
parser.add_argument('language', choices = ['slovak', 'czech', 'english', 'hungarian', 'polish'])
parser.add_argument('infiles',  type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('infilej',  type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('outfile',  nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

inteamss = json.load(args.infilej)
inteamsj = json.load(args.infiles)
outteams = []

for inf in [inteamss, inteamsj]:
    for team in inf:
        outteams.append({
            'id':       int(team['number']) % 1000,
            'name':     team['teamname'],
            'language': args.language,
        })

out = {
    'name':     args.name,
    'number':   args.number,
    'teams':    outteams,
}

yaml.dump(out, args.outfile, allow_unicode = True, default_flow_style = False)
