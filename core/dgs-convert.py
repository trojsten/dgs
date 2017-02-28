#!/usr/bin/python3

import os, sys, re, argparse, colorama
from colorama import Fore as cf
    
def fail():
    print(cf.RED + "dgs-convert: failure")
    sys.exit(1)

colorama.init()

parser = argparse.ArgumentParser(
    description             = "DeGeŠ Markdown conversion utility",
)
parser.add_argument('format',   choices = ['latex', 'html'])
parser.add_argument('infile',   nargs = '?', type = argparse.FileType('r'), default = sys.stdin)
parser.add_argument('outfile',  nargs = '?', type = argparse.FileType('w'), default = sys.stdout) 
args = parser.parse_args()

try:
    tempfile = open('.convert-temp', 'w')

    for line in args.infile:
        line = re.sub(r'^%(.*)$', '', line)
        line = re.sub(r'^"', '„', line)
        line = re.sub(r' "', ' „', line)
        line = re.sub(r'"', '“', line)
        if args.format == 'latex':
            line = re.sub(r'^@H(.*)$', '', line)
            line = re.sub(r'^@E\s*(.*)$', '\\errorMessage{\g<1>}', line)
            line = re.sub(r'^@L(.*)$', '\g<1>', line)
            line = re.sub(r'^@P', '\insertPicture', line)
            line = re.sub(r'^@TODO\s*(.*)$', '\\\\todoMessage{\g<1>}', line)
        if args.format == 'html':
            line = re.sub(r'^@L(.*)$', '', line)
            line = re.sub(r'^@H(.*)$', '\g<1>', line) 
            line = re.sub(r'^@P{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}', '<figure><img src="obrazky/\g<1>.\g<3>" width="500px" alt="\g<5>"/><figcaption>\g<5></figcaption></figure>', line)
        tempfile.write(line)
    
    tempfile.close()
    
    assert os.system('pandoc -R -S --no-tex-ligatures --mathjax --from markdown --latex-engine=xelatex --to {0} -F {3}/core/dgs-filter.py --output="{2}" {1}'.format(args.format, tempfile.name, args.outfile.name, os.getcwd())) == 0
    
    os.remove(tempfile.name)
except IOError as e:
    print(cf.RED + __file__ + ": Could not create temporary file")
    fail()
except AssertionError as e:
    print(cf.RED + __file__ + ": Calling pandoc failed")
    fail()
else:
    print(cf.GREEN + "dgs-convert: success")
    sys.exit(0)

