#!/usr/bin/env python3

import argparse
import yaml
import os
import pprint
from utils import readableDir

parser = argparse.ArgumentParser(
    description="Cut an invite",
)
parser.add_argument('infile', type=argparse.FileType('r'))
parser.add_argument('metafile', type=argparse.FileType('r'))
parser.add_argument('-o', '--output', action=readableDir)
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

children_meta = yaml.load(args.metafile)

pprint.pprint(children_meta['children'])

n = 1
for child in children_meta['children']:
    os.system(f"pdftk {args.infile.name} cat {n}-{n + 1} output Pozvánka-{child['name']}-{child['surname']}.pdf")
    n += 2
