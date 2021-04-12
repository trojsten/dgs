#!/usr/bin/env python3

import argparse, os, sys

from mdcheck import check, exceptions
from utilities import colour as c





class StyleEnforcer():
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="DeGeŠ Markdown style checker",
        )
        self.parser.add_argument('infiles', nargs='+', type=argparse.FileType('r'), default=[sys.stdin])
        self.parser.add_argument('-v', '--verbose', action='store_true')
        self.parser.add_argument('-w', '--warnings', action='store_true')
        self.args = self.parser.parse_args()

    def check(self):
        for filename in self.args.infiles:
            if self.check_markdown_file(filename):
                pass

    def check_markdown_file(self, file):
        ok = True

        try:
            check.encoding(file.name)
        except check.EncodingError as e:
            print("File {name} is not valid: {message}".format(
                name            = colour(file.name, 'name'),
                message         = colour(e.message, 'error'),
            ))
            return False

        line_errors = [
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
            check.FailOnSearch('[Mm]ôžme', "It's spelled \"môžeme\"...", offset=2),
            check.FailOnSearch('[Tt]ohoto', "It's spelled \"tohto\"...", offset=3),
            check.FailOnSearch('t\.j\.', "\"t.j.\" needs spaces (\"t. j.\")"),
            check.FailOnSearch('\\\\text(rm)?\{[.,;]\}', "No need to enclose punctuation in \\text"),
            check.FailOnSearch('\\\\((arc)?(cos|sin|tan|cot|log|ln))\{\((\\\\)?.+\)\}', "Omit parentheses in simple functions"),
            check.LineLength(),
            check.EqualsSpaces(),
            check.DoubleDollars(),
        ]

        line_warnings = [
            check.FailOnSearch('\stak\s', "tak", offset=1),
        ]

        for number, line in enumerate(file):
            ok = all([self.check_line(checker, file, number, line) for checker in line_errors])

            if self.args.warnings:
                ok |= all([self.check_line(checker, file, number, line) for checker in line_warnings])

        if self.args.verbose and ok:
            print(f"File {c.ok('OK')}: {c.name(filename.name)}")

    def check_line(self, checker, file, number, line):
        try:
            checker.check(line)
            return True
        except exceptions.SingleLineError as e:
            print(f"File {c.name(file.name)} line {c.num(number + 1)}: {c.err(e.message)}")
            print(line, end='' if line[-1] == '\n' else '\n')
            print('-' * (e.column) + '^')
        return False


StyleEnforcer().check()
