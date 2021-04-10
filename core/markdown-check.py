#!/usr/bin/env python3

import argparse, os, sys

from mdcheck import check, exceptions
from utilities import colour as c


def check_single_line(line):
    check.double_space(line)
    check.equal_spaces(line)
    check.double_dollars(line)
    check.too_long(line)
    check.trailing_whitespace(line)
    check.tabs(line)
    check.frac_without_brace(line)
    check.circ(line)


def check_markdown_file(file):
    ok = True

    try:
        check.encoding(file.name)
    except check.EncodingError as e:
        print("File {name} is not valid: {message}".format(
            name            = colour(file.name, 'name'),
            message         = colour(e.message, 'error'),
        ))
        return False

    line_checks = [
        check.FailOnSearch('\t', "Tabs instead of spaces"),
        check.FailOnSearch(',[^\s]', "Comma not followed by whitespace"),
        check.FailOnSearch('[ \t]$', "Trailing whitespace"),
        check.FailOnSearch('\\\\frac[^{]', "\\ frac not followed by a brace", offset=5),
        check.FailOnSearch('(?:SI\{[^},]*),', "Comma in \\SI expression", offset=0),
        check.FailOnSearch('(?:\\num\{[^},]*),', "Comma in \\num expression"),
        check.FailOnSearch('\\\\varepsilon', "\\varepsilon is not allowed, use plain \\epsilon"),
        check.FailOnSearch('\^\{?\\\\circ\}?', "\\circ is not allowed, use \\ang{...} instead", offset=2),
        check.FailOnSearch('{\s', "Left brace { followed by whitespace"),
        check.FailOnSearch('\s}', "Right brace } preceded by whitespace"),
        check.FailOnSearch('môžme', "It's spelled \"môžeme\"...", offset=2),
        check.FailOnSearch('t\.j\.', "\"t.j.\" needs spaces (\"t. j.\")"),
        check.FailOnSearch('\\\\text\{[.,;]\}', "No need to enclose punctuation in \\text"),
        check.LineLength(),
        check.EqualsSpaces(),
        check.DoubleDollars(),
    ]

    for number, line in enumerate(file):
        for checker in line_checks:
            try:
                checker.check(line)
            except exceptions.SingleLineError as e:
                print(f"File {c.name(file.name)} line {c.num(number + 1)}: {c.err(e.message)}")
                print(line, end='' if line[-1] == '\n' else '\n')
                print('-' * (e.column) + '^')
                ok = False

    return ok

def main():
    parser = argparse.ArgumentParser(
        description="DeGeŠ Markdown style checker",
    )
    parser.add_argument('infiles', nargs='+', type=argparse.FileType('r'), default=[sys.stdin])
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    for filename in args.infiles:
        if check_markdown_file(filename):
            if args.verbose:
                print(f"File {c.ok('OK')}: {c.name(filename.name)}")

main()
