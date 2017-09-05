#!/usr/bin/python3

import os, sys, re, argparse, colorama
from colorama import Fore, Style

def fail():
    print(Fore.RED + "dgs-convert: failure" + Style.RESET_ALL)
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
            line = re.sub(r'^@NP', '\insertPictureSimple', line)
            line = re.sub(r'^@TODO\s*(.*)$', '\\\\todoMessage{\g<1>}', line)
        if args.format == 'html':
            line = re.sub(r'^@L(.*)$', '', line)
            line = re.sub(r'^@H(.*)$', '\g<1>', line) 
            line = re.sub(r'^@P{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}', '<figure><img src="obrazky/\g<1>.\g<3>" style="height: \g<4>" alt="\g<5>"/><figcaption>\g<5></figcaption></figure>', line)
        tempfile.write(line)
    
    tempfile.close()
    
    assert os.system('pandoc -R -S --no-tex-ligatures --mathjax --from markdown --latex-engine=xelatex --to {0} --filter pandoc-eqnos --output="{2}" {1}'.format(
        args.format, tempfile.name, args.outfile.name, os.getcwd()
    )) == 0
    
    os.remove(tempfile.name)
except IOError as e:
    print(Fore.RED + __file__ + ": Could not create temporary file" + Style.RESET_ALL)
    fail()
except AssertionError as e:
    print(Fore.RED + __file__ + ": Calling pandoc failed" + Style.RESET_ALL)
    fail()
else:
    print(Fore.GREEN + "dgs-convert: success" + Style.RESET_ALL)
    sys.exit(0)

