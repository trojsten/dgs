#!/usr/bin/env python3

import argparse, os, sys

import check
from utils import colour

def checkSingleLine(line):
    check.doubleDollars(line)
    check.tooLong(line)
    check.trailingWhitespace(line)

def checkMarkdownFile(file):
    ok = True

    try:
        check.encoding(file.name)
    except check.EncodingError as e:
        print("File {name} is not valid: {message}".format(
            name            = colour(file.name, 'name'),
            message         = colour(e.message, 'error'),
        ))
        return False

    for number, line in enumerate(file):
        try:
            checkSingleLine(line)
        except check.SingleLineError as e:
            print("File {name} line {num}: {message}".format(
                name        = colour(file.name, 'name'),
                message     = colour(e.message, 'error'),
                num         = colour(number, 'no')
            ))
            print(colour(line, 'no', 'hv'), end = '')
            print('-' * (e.column - 2) + '^')
            ok = False

    return ok

def main():
    parser = argparse.ArgumentParser(
        description             = "DeGeŠ Markdown style checker",
    )
    parser.add_argument('infiles',   nargs = '+', type = argparse.FileType('r'), default = [sys.stdin])
    parser.add_argument('-v', '--verbose', action = 'store_true')
    args = parser.parse_args()
    
    for filename in args.infiles:
        if checkMarkdownFile(filename):
            if args.verbose:
                print("File {name} {ok}".format(
                    name    = colour(filename.name, 'name'),
                    ok      = colour('OK', 'ok'),
                ))

main()
