#!/usr/bin/env python3

import os, sys, re, argparse, colorama
from colorama import Fore, Style

r = list()
r.append(re.compile(r'^%(.*)$'))
r.append(re.compile(r'^"'))
r.append(re.compile(r' "'))
r.append(re.compile(r'\("'))
r.append(re.compile(r'"'))
r.append(re.compile(r'^@H(.*)$'))
r.append(re.compile(r'^@E\s*(.*)$'))
r.append(re.compile(r'^@L(.*)$'))
r.append(re.compile(r'^@P'))
r.append(re.compile(r'^@NP'))
r.append(re.compile(r'^@TODO\s*(.*)$'))
r.append(re.compile(r'^@L(.*)$'))
r.append(re.compile(r'^@H(.*)$'))
r.append(re.compile(r'^@P{(.*?)}{(.*?)}{(.*?)}{(.*?)}{(.*)}{(.*?)}$'))
r.append(re.compile(r'<figcaption style="text-align: center; font-style: italic;">\n</figcaption>'))
r.append(re.compile(r'<strong>¿fig:(.*?)\?</strong>'))

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
        line = r[0].sub('', line)
        line = r[1].sub('„', line)
        line = r[2].sub(' „', line)
        line = r[3].sub('(„', line)
        line = r[4].sub('“', line)
        if args.format == 'latex':
            line = r[5].sub('', line)
            line = r[6].sub('\\\\errorMessage{\g<1>}', line)
            line = r[7].sub('\g<1>', line)
            line = r[8].sub('\\\insertPicture', line)
            line = r[9].sub('\\\insertPictureSimple', line)
            line = r[10].sub('\\\\todoMessage{\g<1>}', line)
        if args.format == 'html':
            line = r[11].sub('', line)
            line = r[12].sub('\g<1>', line)
            line = r[13].sub('<figure id="\g<6>"><img src="obrazky/\g<1>.\g<3>" style="height: \g<4>; margin: auto; display: block;" alt="\g<5>"/><figcaption style="text-align: center; font-style: italic;">\g<5></figcaption></figure>', line)
        tempfile.write(line)

    tempfile.close()

    assert os.system('pandoc -R -S --no-tex-ligatures --mathjax --from markdown --latex-engine=xelatex --to {0} --filter pandoc-crossref -M "crossrefYaml=core/crossref.yaml" --output="{2}" {1}'.format(
        args.format, tempfile.name, args.outfile.name, os.getcwd()
    )) == 0

    if args.format == 'html':
        with open(args.outfile.name, "r+") as f:
            s = f.read()
            f.seek(0)
            s = r[14].sub('', s)
            s = r[15].sub('<a class="figref" href="#fig:\g<1>"> \g<1> </a>', s)
            f.write('<style>body{counter-reset:image;}figcaption::before{counter-increment: image; font-style: normal; content: "Obrázok " counter(image) ":";}</style>\n' + s)

#    os.remove(tempfile.name)
except IOError as e:
    print(Fore.RED + __file__ + ": Could not create temporary file" + Style.RESET_ALL)
    fail()
except AssertionError as e:
    print(Fore.RED + __file__ + ": Calling pandoc failed" + Style.RESET_ALL)
    fail()
else:
    print(Fore.GREEN + "dgs-convert: success" + Style.RESET_ALL)
    sys.exit(0)

