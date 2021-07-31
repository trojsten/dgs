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
            check.FailOnSearch(r'\t', "Tabs instead of spaces"),
            check.CommaSpace(),
            check.FailOnSearch(r'[ \t]$', "Trailing whitespace"),
            check.FailOnSearch(r'\\frac[^{]', "\\frac not followed by a brace", offset=5),
            check.FailOnSearch(r'(?:SI\{[^},]*),', "Comma in \\SI expression", offset=0),
            check.FailOnSearch(r'(?:\\num\{[^},]*),', "Comma in \\num expression"),
            check.FailOnSearch(r'\\varepsilon', "\\varepsilon is not allowed, use plain \\epsilon"),
            check.FailOnSearch(r'\^\{?\\circ\}?', "\\circ is not allowed, use \\ang{...} instead", offset=2),
            check.FailOnSearch(r'{\s+[^\s]', "Left brace { followed by whitespace"),
            check.FailOnSearch(r'[^\s]\s+}', "Right brace } preceded by whitespace"),
            check.FailOnSearch(r'[Mm]ôžme', "It's spelled \"môžeme\"...", offset=2),
            check.FailOnSearch(r'[Tt]ohoto', "It's spelled \"tohto\"...", offset=3),
            check.FailOnSearch(r't\.j\.', "\"t.j.\" needs spaces (\"t. j.\")"),
            check.FailOnSearch(r'\\text(rm)?\{[.,;]\}', "No need to enclose punctuation in \\text"),
            check.FailOnSearch(r'\\((arc)?(cos|sin|tan|cot|log|ln))\{\((\\)?.+\)\}', "Omit parentheses in simple functions"),
            check.LineLength(),
            check.EqualsSpaces(),
            check.PlusSpaces(),
            check.DoubleDollars(),
        ]

        line_warnings = [
            check.FailOnSearch(r'\btak\b(?!,)', "Do you really need this \"tak\" here?", offset=1),
            check.Parentheses(),
        ]

        for number, line in enumerate(file):
            ok = all([self.check_line(checker, file, number, line) for checker in line_errors])

            if self.args.warnings:
                ok &= all([self.check_line(checker, file, number, line, cfunc=c.warn) for checker in line_warnings])

        if self.args.verbose and ok:
            print(f"File {c.ok('OK')}: {c.path(file.name)}")

    def check_line(self, checker, file, number, line, *, cfunc=c.err):
        try:
            checker.check(line)
            return True
        except exceptions.SingleLineError as e:
            print(f"File {c.path(file.name)} line {c.num(number + 1)}: {cfunc(e.message)}")
            print(line, end='' if line[-1] == '\n' else '\n')
            print('-' * (e.column) + '^')
            return False


StyleEnforcer().check()
