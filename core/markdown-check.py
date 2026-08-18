#!/usr/bin/env python

import argparse
import copy
import subprocess
import sys
from pathlib import Path

import regex as re
import i18n
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
        self.parser.add_argument('--only', nargs='+', type=str)
        self.parser.add_argument('--ignore', nargs='+', type=str)
        self.parser.add_argument('--markdown', action='store_true')
        self.args = self.parser.parse_args()

        self.commented = re.compile(r'^%')

        self.line_errors = {
            'tab': check.FailIfFound(r'\t', "Tab instead of spaces"),
            'cws': check.FailIfFound(r',[^\s^]', "Comma not followed by whitespace"),
            # siunitx separates list arguments with `;`, so a semicolon inside `\Coord{...}`,
            # `\qtylist{...}` or `\ang{...}` is the syntax, not a punctuation slip. The exemptions
            # used to demand a numeric argument (`[0-9.e;]+`) and no option group, which flagged
            # both `\Coord{R;H}` and `\qtylist[list-units=single]{4;2;...}` -- symbolic coordinates
            # and any listed unit option. Match the whole argument up to the semicolon instead.
            # `[^}]*` rather than `[^};]*`: a list has a semicolon between every pair of items, and
            # the exemption has to reach back past the earlier ones to the opening brace.
            'sws': check.FailIfFound(r'(?<!\\(?:ang|qtylist|Coord)(?:\[[^\]]*\])?{[^}]*);[^\s]',
                                     "Semicolon not followed by whitespace"),
            'pas': check.ParenthesesSpace(),
            # `(?! )[ \t]$` could never fire on a trailing space: the lookahead is evaluated at
            # the very position `[ \t]` then consumes, so a space failed its own guard and only a
            # tab was ever reported. 14 of volume 28's files had trailing spaces and passed.
            'tws': check.FailIfFound(r'[ \t]+$', "Trailing whitespace"),
            'spb': check.FailIfFound(r'[^ ]\\\\$', "No space before ending \\\\", offset=1),
            'frb': check.FailIfFound(r'\\frac[^{]', "\\frac not followed by a brace", offset=5),
            'csi': check.FailIfFound(r'(?:qty\{[^},]*),', "Comma in \\qty expression", offset=0),
            'osi': check.FailIfFound(r'\\SI', "Use \\qty instead of SI"),
            'cnu': check.FailIfFound(r'(?:\\num\{[^},]*),', "Comma in \\num expression"),
            'vep': check.FailIfFound(r'\\varepsilon', "\\varepsilon is not allowed, use plain \\epsilon"),
            'crc': check.FailIfFound(r'\^\{?\\circ\}?', "\\circ is not allowed, use \\ang{...} instead", offset=2),
            'lbw': check.FailIfFound(r'(?<!\\text){\s+[^\s]', "Left brace { followed by whitespace"),
            'rbw': check.FailIfFound(r'[^\s]\s+}', "Right brace } preceded by whitespace", offset=2),
            # `\,` cannot be written in Markdown: a backslash before punctuation is an escape,
            # so `d.\,h.` reaches the TeX as `d.,h.` -- a literal comma in the middle of a word.
            # The rule stays, then, but now says what to write instead. `\;` and `\.` are the
            # same trap.
            'tgc': check.FailIfFound(r'\\[,;.]', "Escapes to a literal character in Markdown; "
                                              "use \\thinspace for a thin space"),
            'tjs': check.FailIfFound(r't\.j\.', "\"t.j.\" needs spaces (\"t. j.\")"),
            'pun': check.FailIfFound(r'\\text(rm)?\{[.,; ]+\}', "No need to enclose punctuation in \\text"),
            'sum': check.FailIfFound(r'\\sum\b', "Use \\Sum[]{} instead"),
            'int': check.FailIfFound(r'\\int\b', "Use \\Int[]{}{} instead"),
            'imp': check.FailIfFound(r'\\implies', "Use \\Implies instead"),
            'rar': check.FailIfFound(r'\\Rightarrow', "You probably want to use \\Implies instead"),
            'txp': check.FailIfFound(r'\\text(it|bf|sf)', "Do not use TeX font styling"),
            'txs': check.FailIfFound(r'\\(sub)?section', "Do not use TeX headings"),
            'txf': check.FailIfFound(r'\\footnote', "Do not use TeX footnotes"),
            'lip': check.FailIfFound(r'\\insertPicture', "Do not use legacy custom figure commands"),
            # `~` used to be in this class, which made every `~~strikethrough~~` a "fancy Unicode
            # dash" -- three false positives in `28/circle-squared` alone. It is not a dash or a
            # quote and does not belong here. It was not moved to a rule of its own either: the
            # only lone `~` anywhere in `source/` sits in `~user` URL paths, so such a rule would
            # report nothing but false positives.
            'uni': check.FailIfFound(r'[“”’–—]', "Do not use fancy Unicode dashes or quotation marks in the source"),
            'opa': check.FailIfFound(r'\\((arc)?(cos|sin|tan|cot|log|ln))\{\((\\)?.+\)\}',
                              "Omit parentheses in simple functions"),
            'cmk': check.ConflictMarkers(),
            'eqs': check.EqualsSpaces(),
            'cdt': check.CdotSpaces(),
            'sie': check.SIExponents(),
            'lln': check.LineLength(),
            'pws': check.PlusSpaces(),
            'dds': check.DoubleDollars(),
            'rfc': check.Reference(),
        }

        # Spelling rules for one language only. They used to sit in `line_errors` and so ran on
        # every translation: `tohoto` is a misspelling of Slovak `tohto` but the correct Czech word,
        # so every Czech file that used it was reported. Keyed by the language directory the file
        # sits in, and skipped entirely for a path with no language in it.
        self.language_errors = {
            'sk': {
                'mzm': check.FailIfFound(r'[Mm]ôžme', "It's spelled \"môžeme\"...", offset=2),
                'tht': check.FailIfFound(r'[Tt]ohoto', "It's spelled \"tohto\"...", offset=3),
            },
        }

        self.line_warnings = {
            'tak': check.FailIfFound(r'\btak\b(?!,)', "Do you really need this \"tak\" here?", offset=1),
            # check.Parentheses(),
        }

    def language_of(self, path: Path) -> str | None:
        """
        The language a source file is written in, or None if the path does not say.

        Every module puts the language in a directory name, but at a different depth
        (`.../problems/<problem>/<language>/solution.md` in `naboj`), so match on the
        set of known languages rather than on a fixed index.
        """
        for part in reversed(path.parts):
            if part in i18n.languages:
                return part
        return None

    def check(self):
        for path in self.args.infiles:
            if self.args.markdown:
                self.check_markdown(path)
            self.check_markdown_file(path)

    def check_label(self, module, path, label):
        if module == 'naboj':
            volume_id, problem_id, _language, _filename = path.parts()[-4:-1]
            # if matched := re.match(fr'#(eq|fig|tbl):(?P<problem>[]):[\w]+', label):
        elif module == 'seminar':
            volume_id, semester_id, round_id, problem_id = path.split[2:5]
            assert re.search(
                fr'#eq:(?P<id>{volume_id:02d}{semester_id:1d}{round_id:1d}{problem_id:02d}):(?P<title>\w+)', label)

    def check_markdown_file(self, path):
        module = path.parts[1]
        problem_id = path.parents[1].stem

        self.problem_errors = {
            'lfn': check.FailIfFound(fr'{{-?(#|@)(eq|fig|sec):(?!{problem_id})\}}', "Label does not match file name"),
            'lne': check.FailIfFound(fr'{{-?(#|@)(eq|fig|sec):{problem_id}[^ ]\}}', "Non-empty label in problem"),
        }

        self.solution_errors = {
            'lfn': check.FailIfFound(fr'{{(#|@)(eq|fig|sec):(?!{problem_id})\}}', "Label does not match file name"),
            'lne': check.FailIfFound(fr'{{(#|@)(eq|fig|sec):{problem_id}[^:]\}}', "Empty or mismatching label in solution"),
        }

        self.answer_errors = {
            'fra': check.FailIfFound(r'\\frac\b', "Use \\dfrac in answers")
        }

        try:
            check.encoding(path)
        except exceptions.EncodingError as e:
            print(f"File {c.name(path.name)} is not valid: {c.err(e.message)}")
            return False

        line_errors = copy.copy(self.line_errors)
        line_errors |= self.language_errors.get(self.language_of(path), {})

        if path.name == 'problem.md':
            line_errors |= self.problem_errors

        if path.name == 'solution.md':
            line_errors |= self.solution_errors

        if path.name == 'answer.md':
            line_errors |= self.answer_errors

        if self.args.only is not None:
            line_errors = {key: error for key, error in line_errors.items() if key in self.args.only}

        if self.args.ignore is not None:
            for key in self.args.ignore:
                del line_errors[key]

        with open(path, 'r') as file:
            ok = None
            for number, line in enumerate(file):
                ok = all(self.check_line(checker, module, path, number, line) for checker in line_errors.values())

                if self.args.warnings:
                    ok &= all(self.check_line(checker, module, path, number, line, cfunc=c.warn)
                               for checker in self.line_warnings.values())

            if self.args.verbose and ok:
                print(f"File {c.path(file.name)} {c.ok('OK')}")
            return ok

    def check_markdown(self, path):
        out = subprocess.check_output(['pandoc', '--from', 'markdown+smart', '--to', 'native', path],
                                      encoding='utf-8').split("\n")

        for line in out:
            try:
                if matches := re.search(
                        r'(Format "tex").*(?P<si>\\\\(SI|SIrange|SIlist|num|numrange|numlist|ang|si)({[^}]+})+)', line):
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


try:
    StyleEnforcer().check()
except subprocess.CalledProcessError:
    print("No files found")
