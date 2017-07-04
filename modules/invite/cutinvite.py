#!/usr/bin/python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import jinjaEnv, mergeInto, renderList, readableDir
from colorama import Fore, Style

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ round from repository",
)
parser.add_argument('infile',           type = argparse.FileType('r')) 
parser.add_argument('metafile',         type = argparse.FileType('r')) 
parser.add_argument('-o', '--output',   action = readableDir) 
parser.add_argument('-v', '--verbose',  action = 'store_true')
args = parser.parse_args()

if (args.verbose):
    pprint.pprint(context)
print(args.metafile)

childrenMeta        = yaml.load(args.metafile)

pprint.pprint(childrenMeta['children'])

n = 1
for child in childrenMeta['children']:
    os.system("pdftk {input} cat {nfrom}-{nto} output {name}".format(
        input = args.infile.name,
        nfrom = n,
        nto = n + 1,
        name = '"Pozvánka-{}-{}.pdf"'.format(child['name'], child['surname']),
    ))
    n += 2

