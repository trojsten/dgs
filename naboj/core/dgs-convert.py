#!/usr/bin/python3.4

import os, sys, re, argparse

parser = argparse.ArgumentParser(
    description             = "DeGeŠ Náboj conversion utility",
)
parser.add_argument('infile',   nargs = '?', type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('outfile',  nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

tempfile = open('.convert-temp', 'w')

for line in args.infile:
    line = re.sub(r'^%(.*)$', '', line)
    line = re.sub(r'^"', '„', line)
    line = re.sub(r' "', ' „', line)
    line = re.sub(r'"', '“', line)
    tempfile.write(line)

tempfile.close()

os.rename(tempfile.name, args.outfile.name)

print("dgs-convert.py: success")
