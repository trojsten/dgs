#!/usr/bin/python3.4

import os, sys, re, argparse

parser = argparse.ArgumentParser(
	description				= "DeGeŠ Markdown conversion utility",
)
parser.add_argument('format',	choices = ['latex', 'html'])
parser.add_argument('infile',	nargs = '?', type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('outfile',	nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

tempfile = open('.convert-temp', 'w')

for line in args.infile:
	line = re.sub(r'^%(.*)$', '', line)
	line = re.sub(r'(\s)"', '\g<1>„', line)
	line = re.sub(r'"', '“', line)
	if args.format == 'latex':
		line = re.sub(r'^@H(.*)$', '', line)
		line = re.sub(r'^@L(.*)$', '\g<1>', line) 
	if args.format == 'html':
		line = re.sub(r'^@L(.*)$', '', line)
		line = re.sub(r'^@H(.*)$', '\g<1>', line) 
	tempfile.write(line)

tempfile.close()

os.system('pandoc -R -S --mathjax --from markdown --latex-engine=xelatex --to {0} -F {3}/core/dgs-filter.py --output="{2}" {1}'.format(args.format, tempfile.name, args.outfile.name, os.getcwd()))

os.remove(tempfile.name)

print("dgs-convert.py: success")

'''
if ! pandoc --version 2>/dev/null | grep -Eq 'pandoc 1\.(12\.[3-9]|1[3-9])'; then
  echo $'\e[1;31m'"Error: _convert.sh depends on pandoc 1.12.3."$'\e[0m'
  exit 1
fi

if [ "${output%.tex}" != "$output" ]; then
  format=latex
  sedfilter='/^%/d; /^@[^L]/d; s/^@L \?//'
elif [ "${output%.html}" != "$output" ]; then
  format=html
  sedfilter='/^%/d; /^@[^H]/d; s/^@H \?//'
else
  echo -e "\e[31mOutput file format is neither .tex nor .html\e[0m"
  exit 1
fi

sed "$sedfilter" <"$input" |
  pandoc -R -S --mathjax -f markdown --latex-engine=xelatex -t "$format" -F "$(dirname "$0")"/dgs-filter.py -o "$output"
'''
