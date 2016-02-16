#!/usr/bin/python3.4

import os, sys, re, argparse

parser = argparse.ArgumentParser(
	description				= "DeGeŠ Markdown conversion utility",
)
parser.add_argument('format',	choices = ['tex', 'html'])
parser.add_argument('infile',	nargs = '?', type = argparse.FileType('r'),	default = sys.stdin)
parser.add_argument('outfile',	nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

for line in args.infile:
	line = re.sub(r'^\%', '', line)
	line = re.sub(r'(\s)"', '\g<1>„', line)
	line = re.sub(r'"', '“', line)
	if format == 'tex':
		line = re.sub(r'^\@H', '', line)	
	if format == 'html':
		line = re.sub(r'^\@L', '', line)
	args.outfile.write(line)

exit(0)

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
