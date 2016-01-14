#!/bin/bash

# skonvertuje markdown na tex alebo html, pricom:
# - riadky zacinajuce "%" su komentare a vzdy ich ignorujeme
# - riadky zacinajuce "@H" sa pouziju iba ked generujeme HTML
# - riadky zacinajuce "@L" sa pouziju iba ked generujeme LaTeX
# - _filter.py zabezpeci specialnu syntax ako napr. ```vstup a ```vystup

if [ "$#" != 2 ]; then
  echo "usage:
  $0 x.md x.tex
  $0 x.md x.html"
  exit 1
fi

if ! pandoc --version 2>/dev/null | grep -Eq 'pandoc 1\.(12\.[3-9]|1[3-9])'; then
  echo $'\e[1;31m'"Error: _convert.sh depends on pandoc 1.12.3."$'\e[0m'
  exit 1
fi

input=$1
output=$2

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
