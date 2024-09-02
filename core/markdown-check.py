#!/usr/bin/env python

import argparse
import sys
import re
import copy
import subprocess

from pathlib import Path

from mdcheck import check, exceptions
from utilities import colour as c


class StyleEnforcer:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="DeGeŠ Markdown style checker",
        )
        self.parser.add_argument('infiles', nargs='+', type=Path, default=[sys.stdin])
        self.parser.add_argument('-v', '--verbose', action='store_true')
        self.parser.add_argument('-w', '--warnings', action='store_true')
        self.args = self.parser.parse_args()

        self.commented = re.compile(r'^%')

        self.line_errors = [
            check.FailIfFound(r'\t', "Tab instead of spaces"),
            check.FailIfFound(r',[^\s^]', "Comma not followed by whitespace"),
            check.FailIfFound(r'(?!\\ang{);[^\s]', "Semicolon not followed by whitespace"),
            check.ParenthesesSpace(),
            check.FailIfFound(r'(?! )[ \t]$', "Trailing whitespace"),
            check.FailIfFound(r'[^ ]\\\\$', "No space before ending \\\\", offset=1),
            check.FailIfFound(r'\\frac[^{]', "\\frac not followed by a brace", offset=5),
            check.FailIfFound(r'(?:SI\{[^},]*),', "Comma in \\SI expression", offset=0),
            check.FailIfFound(r'(?:\\num\{[^},]*),', "Comma in \\num expression"),
            check.FailIfFound(r'\\varepsilon', "\\varepsilon is not allowed, use plain \\epsilon"),
            check.FailIfFound(r'\^\{?\\circ\}?', "\\circ is not allowed, use \\ang{...} instead", offset=2),
            check.FailIfFound(r'(?<!\\text){\s+[^\s]', "Left brace { followed by whitespace"),
            check.FailIfFound(r'[^\s]\s+}', "Right brace } preceded by whitespace", offset=2),
            check.FailIfFound(r'[Mm]ôžme', "It's spelled \"môžeme\"...", offset=2),
            check.FailIfFound(r'[Tt]ohoto', "It's spelled \"tohto\"...", offset=3),
            check.FailIfFound(r'\\,', "You should not use typographic corrections"),
            check.FailIfFound(r'\\thinspace', "You should not use typographic corrections"),
            check.FailIfFound(r't\.j\.', "\"t.j.\" needs spaces (\"t. j.\")"),
            check.FailIfFound(r'\\text(rm)?\{[.,;]\}', "No need to enclose punctuation in \\text"),
            check.FailIfFound(r'\\sum\b', "Use \\Sum[]{} instead"),
            check.FailIfFound(r'\\int\b', "Use \\Int[]{}{} instead"),
            check.FailIfFound(r'\\implies', "Use \\Implies instead"),
            check.FailIfFound(r'\\Rightarrow', "You probably want to use \\Implies instead"),
            check.FailIfFound(r'[“”’–—~]', "Do not use fancy Unicode dashes or quotation marks in the source"),
            check.FailIfFound(r'\\insertPicture', "Do not use TeX commands to include pictures"),
            check.FailIfFound(r'\\text(it|bf|sf)', "Do not use TeX commands to change font"),
            check.FailIfFound(r'\\footnote', "Do not use TeX commands to include footnotes"),
            check.FailIfFound(r'\\((arc)?(cos|sin|tan|cot|log|ln))\{\((\\)?.+\)\}',
                              "Omit parentheses in simple functions"),
            check.ConflictMarkers(),
            check.EqualsSpaces(),
            check.CdotSpaces(),
            check.SIExponents(),
            check.LineLength(),
            check.PlusSpaces(),
            check.DoubleDollars(),
            check.Reference(),
        ]

        self.line_warnings = [
            check.FailIfFound(r'\btak\b(?!,)', "Do you really need this \"tak\" here?", offset=1),
            # check.Parentheses(),
        ]

    def check(self):
        for path in self.args.infiles:
            self.check_markdown(path)
            self.check_markdown_file(path)

    def check_label(self, module, path, label):
        if module == 'naboj':
            volume_id, problem_id, language, filename = path.parts()[-4:-1]
            print(volume_id, problem_id, language, filename)
            # if matched := re.match(fr'#(eq|fig|tbl):(?P<problem>[]):[\w]+', label):
        elif module == 'seminar':
            volume_id, semester_id, round_id, problem_id = path.split[2:5]
            assert re.search(
                fr'#eq:(?P<id>{volume_id:02d}{semester_id:1d}{round_id:1d}{problem_id:02d}):(?P<title>\w+)', label)

    def check_markdown_file(self, path):
        module = path.parts[1]
        problem_id = path.parents[1].stem

        self.problem_errors = [
            check.FailIfFound(fr'{{-?(#|@)(eq|fig|sec):(?!{problem_id})\}}', "Label does not match file name"),
            check.FailIfFound(fr'{{-?(#|@)(eq|fig|sec):{problem_id}[^ ]\}}', "Non-empty label in problem"),
        ]

        self.solution_errors = [
            check.FailIfFound(fr'{{(#|@)(eq|fig|sec):(?!{problem_id})\}}', "Label does not match file name"),
            check.FailIfFound(fr'{{(#|@)(eq|fig|sec):{problem_id}[^:]\}}', "Empty or mismatching label in solution"),
        ]

        self.answer_errors = [
            check.FailIfFound(r'\\frac\b', "Use \\dfrac in answers")
        ]

        try:
            check.encoding(path)
        except exceptions.EncodingError as e:
            print(f"File {c.name(path.name)} is not valid: {c.err(e.message)}")
            return False

        line_errors = copy.copy(self.line_errors)
        if path.name == 'problem.md':
            line_errors += self.problem_errors

        if path.name == 'solution.md':
            line_errors += self.solution_errors

        if path.name == 'answer.md':
            line_errors += self.answer_errors

        with open(path, 'r') as file:
            ok = None
            for number, line in enumerate(file):
                ok = all([self.check_line(checker, module, path, number, line) for checker in line_errors])

                if self.args.warnings:
                    ok &= all([self.check_line(checker, module, path, number, line, cfunc=c.warn)
                               for checker in self.line_warnings])

            if self.args.verbose and ok:
                print(f"File {c.path(file.name)} {c.ok('OK')}")
            return ok

    def check_markdown(self, path):
        out = subprocess.check_output(['pandoc', '--from', 'markdown+smart', '--to', 'native', path],
                                      encoding='utf-8').split("\n")

        for line in out:
            try:
                if matches := re.search(
                        r'(Format "tex").*(?P<si>\\\\(SI|SIrange|SIlist|num|numrange|numlist|ang)({[^}]+})+)', line):
                    si = matches.group('si')
                    raise exceptions.MarkdownError(f"Raw siunitx token \"{si}\"")
#                if matches := re.search(r'Math InlineMath ".*[^ ](?P<symbol>=|\\approx|\\cdot|\\doteq|\+)[^ ].*"', line):
#                    symbol = matches.group('symbol')
#                    raise exceptions.MarkdownError(f"Missing space around \"{symbol}\"")
            except exceptions.MarkdownError as e:
                print(f"File {c.path(path)}: {c.err(e.message)}")

    def check_line(self, checker, module, path, number, line, *, cfunc=c.err):
        if self.commented.match(line):
            return True
        try:
            checker.check(module, path, line)
            return True
        except exceptions.SingleLineError as e:
            print(f"File {c.path(path)} line {c.num(number + 1)}: {cfunc(e.message)}")
            print(line, end='' if line[-1] == '\n' else '\n')
            print('-' * e.column + '^')
            return False


StyleEnforcer().check()
