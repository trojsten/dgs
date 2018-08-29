#!/usr/bin/env python3

import argparse, os, sys

import check
from utils import colour

def checkSingleLine(line):
    if not check.doubleDollars(line):
        raise check.SingleLineError('Double dollars within text', line) 

    return True

def checkMarkdownFile(file):
    ok = True

    for number, line in enumerate(file):
        try:
            checkSingleLine(line)
        except check.SingleLineError as e:
            print("Line {num}: {message} {}".format(
                message     = e.message,
                line        = colour(line, 'error')
            ), end = '')
            ok = False

    return ok

def main():
    parser = argparse.ArgumentParser(
        description             = "DeGeŠ Markdown style checker",
    )
    parser.add_argument('infile',   nargs = '?', type = argparse.FileType('r'), default = sys.stdin)
    args = parser.parse_args()

    if checkMarkdownFile(args.infile):
        print("OK")
        sys.exit(0)
    else:
        print("Not OK")
        sys.exit(1)

main()
