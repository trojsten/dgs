#!/usr/bin/env python3

import os, sys, re, argparse
import tempfile

from utilities import colour as c

def fail():
    print(f"{c.err('dgs-convert: failure')}")
    sys.exit(1)

parser = argparse.ArgumentParser(
    description             = "DeGeŠ Markdown conversion utility",
)
parser.add_argument('format',   choices = ['latex', 'html'])
parser.add_argument('locale',   choices = ['sk', 'cs', 'en', 'fr', 'ru', 'pl'])
parser.add_argument('infile',   nargs = '?', type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('outfile',  nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

quoteOpen, quoteClose = {
    'sk':   ('„', '“'),
    'cs':   ('„', '“'),
    'en':   ('“', '”'),
    'fr':   ('«\ ', '\ »'),
    'ru':   ('«', '»'),
    'pl':   ('„', '”'),
}[args.locale]

try:
    temporaryIn = tempfile.SpooledTemporaryFile(mode = 'w+b')

    tempfile = open('.convert-temp', 'w')
    tempfile2 = open('.convert-temp2', 'w+')

    for line in args.infile:
        line = re.sub(r'^%(.*)$', '', line)
        if args.format == 'latex':
            line = re.sub(r'^@H(.*)$', '', line)
            line = re.sub(r'^@E\s*(.*)$', '\\\\errorMessage{\g<1>}', line)
            line = re.sub(r'^@L(.*)$', '\g<1>', line)
            line = re.sub(r'^@P', '\\\\insertPicture', line)
            line = re.sub(r'^@NP', '\\\\insertPictureSimple', line)
            line = re.sub(r'^@TODO\s*(.*)$', '\\\\todoMessage{\g<1>}', line)
        if args.format == 'html':
            line = re.sub(r'^@L(.*)$', '', line)
            line = re.sub(r'^@H(.*)$', '\g<1>', line) 
            line = re.sub(r'^@P{(.*?)}{(.*?)}{(.*?)}{(.*?)}{(.*)}{(.*?)}$', '<figure><img src="obrazky/\g<1>.\g<3>" style="height: \g<4>" alt="\g<5>"/><figcaption>\g<5></figcaption></figure>', line)
        tempfile.write(line)
    
    tempfile.close()
    
    assert os.system(f'pandoc \
        --mathjax \
        --from markdown-smart \
        --pdf-engine=xelatex \
        --to {args.format} \
        --filter pandoc-crossref -M "crossrefYaml=core/crossref.yaml" \
        --metadata lang=sk-SK \
        --output="{tempfile2.name}" \
        {tempfile.name}'
    ) == 0

    for line in tempfile2:
        line = re.sub(r'"\b', quoteOpen, line)
        line = re.sub(r'"', quoteClose, line)
        args.outfile.write(line)

    args.outfile.close()
    
    os.remove(tempfile.name)
    os.remove(tempfile2.name)

#except IOError as e:
#    print(f"{c.name(__file__)}: Could not create a temporary file")
#    fail()
except AssertionError as e:
    print(f"{c.name(__file__)}: Calling pandoc failed")
    fail()
else:
    print(f"{c.ok('dgs-convert: success')}")
    sys.exit(0)

