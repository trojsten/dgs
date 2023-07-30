#!/usr/bin/env python3

import argparse, os, sys, re

from pathlib import Path

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

        self.commented = re.compile(r'^%')

        self.line_errors = [
            check.FailIfFound(r'\t', "Tab instead of spaces"),
            check.CommaSpace(),
#            check.SemicolonSpace(),
            check.ParenthesesSpace(),
            check.FailIfFound(r'[ \t]$', "Trailing whitespace"),
            check.FailIfFound(r'[^ ]\\\\$', "No space before ending \\\\", offset=1),
            check.FailIfFound(r'\\frac[^{]', "\\frac not followed by a brace", offset=5),
#            check.FailIfFound(r'\$\\SI{.*}{.*}\$', "Solitary \\SI does not have to be enclosed in $$"),
            check.FailIfFound(r'(?:SI\{[^},]*),', "Comma in \\SI expression", offset=0),
            check.FailIfFound(r'(?:\\num\{[^},]*),', "Comma in \\num expression"),
            check.FailIfFound(r'\\varepsilon', "\\varepsilon is not allowed, use plain \\epsilon"),
            check.FailIfFound(r'\^\{?\\circ\}?', "\\circ is not allowed, use \\ang{...} instead", offset=2),
            check.FailIfFound(r'{\s+[^\s]', "Left brace { followed by whitespace"),
            check.FailIfFound(r'[^\s]\s+}', "Right brace } preceded by whitespace"),
            check.FailIfFound(r'[Mm]ôžme', "It's spelled \"môžeme\"...", offset=2),
            check.FailIfFound(r'[Tt]ohoto', "It's spelled \"tohto\"...", offset=3),
            check.FailIfFound(r'\\,', "You should not use typographic corrections"),
            check.FailIfFound(r'\\thinspace', "You should not use typographic corrections"),
            check.FailIfFound(r't\.j\.', "\"t.j.\" needs spaces (\"t. j.\")"),
            check.FailIfFound(r'\\text(rm)?\{[.,;]\}', "No need to enclose punctuation in \\text"),
            check.FailIfFound(r'\\((arc)?(cos|sin|tan|cot|log|ln))\{\((\\)?.+\)\}', "Omit parentheses in simple functions"),
            check.ConflictMarkers(),
            check.EqualsSpaces(),
            check.CdotSpaces(),
            check.SIExponents(),
            check.LineLength(),
            check.PlusSpaces(),
            check.DoubleDollars(),
        ]

        self.line_warnings = [
            check.FailIfFound(r'\btak\b(?!,)', "Do you really need this \"tak\" here?", offset=1),
            #check.Parentheses(),
        ]

    def check(self):
        for filename in self.args.infiles:
            if self.check_markdown_file(filename):
                pass

    def check_markdown_file(self, file):
        path = Path(file.name)
        problem_id = Path(file.name).parent.stem

        try:
            check.encoding(path)
        except exceptions.EncodingError as e:
            print(f"File {c.name(file.name)} is not valid: {c.err(e.message)}")
            return False

        line_errors = self.line_errors
#        if path.name == 'problem.md':
#            line_errors = self.line_errors + [
#                check.FailIfFound(fr'(#|@)(eq|fig|sec):(?!{problem_id})', "Label does not match file name"),
#                check.FailIfFound(fr'(#|@)(eq|fig|sec):{problem_id}[^ ]', "Non-empty label in problem"),
#            ]
#
#        if path.name == 'solution.md':
#            line_errors = self.line_errors + [
#                check.FailIfFound(fr'(#|@)(eq|fig|sec):(?!{problem_id}:)', "Label does not match file name"),
#            ]

        for number, line in enumerate(file):
            ok = all([self.check_line(checker, file, number, line) for checker in line_errors])

            if self.args.warnings:
                ok &= all([self.check_line(checker, file, number, line, cfunc=c.warn) for checker in self.line_warnings])

        if self.args.verbose and ok:
            print(f"File {c.path(file.name)} {c.ok('OK')}")

    def check_line(self, checker, file, number, line, *, cfunc=c.err):
        if self.commented.match(line):
            return True
        try:
            checker.check(line)
            return True
        except exceptions.SingleLineError as e:
            print(f"File {c.path(file.name)} line {c.num(number + 1)}: {cfunc(e.message)}")
            print(line, end='' if line[-1] == '\n' else '\n')
            print('-' * (e.column) + '^')
            return False


StyleEnforcer().check()
