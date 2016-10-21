#!/usr/bin/python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf

colorama.init()


parser = argparse.ArgumentParser(
    description             = "Create a PDF bar code",
)
parser.add_argument('team', type = int)
parser.add_argument('problem', type = int)
args = parser.parse_args()

code = "47{:03d}{:03d}".format(args.team, args.problem)
filename = "input/barcodes/barcode-{:03d}{:03d}.pdf".format(args.team, args.problem)

string = """barcode -e "39" -b "{code}" -g "100x25" -o barcode.ps && ps2pdf barcode.ps barcode1.pdf && pdfcrop barcode1.pdf {outfile}""".format(code = code, outfile = filename)
os.system(string)
