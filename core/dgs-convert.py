#!/usr/bin/python3.4

import os, sys, re, argparse

parser = argparse.ArgumentParser(
    description             = "DeGeŠ Markdown conversion utility",
)
parser.add_argument('format',   choices = ['latex', 'html'])
parser.add_argument('infile',   nargs = '?', type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('outfile',  nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

tempfile = open('.convert-temp', 'w')

for line in args.infile:
    line = re.sub(r'^%(.*)$', '', line)
    if args.format == 'latex':
        line = re.sub(r'^@H(.*)$', '', line)
        line = re.sub(r'^@L(.*)$', '\g<1>', line)
        line = re.sub(r'^@P', '\insertPicture', line)
    if args.format == 'html':
        line = re.sub(r'^@L(.*)$', '', line)
        line = re.sub(r'^@H(.*)$', '\g<1>', line) 
        line = re.sub(r'^@P{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}', '<figure><img src="\g<1>.\g<3>" width="500px" alt="\g<5>"/><figcaption>\g<5></figcaption></figure>', line)
    tempfile.write(line)

tempfile.close()

os.system('pandoc -R -S --mathjax --from markdown --latex-engine=xelatex --to {0} -F {3}/core/dgs-filter.py --output="{2}" {1}'.format(args.format, tempfile.name, args.outfile.name, os.getcwd()))

os.remove(tempfile.name)

print("dgs-convert.py: success")
