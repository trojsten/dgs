import codecs
import logging
from abc import ABCMeta, abstractmethod

import regex as re
from mdcheck import exceptions

log = logging.getLogger('root')
log.setLevel(logging.WARNING)



class LineChecker(metaclass=ABCMeta):
    @abstractmethod
    def check(self, module, path, line):
        pass


class FailIfFound(LineChecker):
    """ Simply fails if `regex` matches the line """
    def __init__(self, regex, message, *, offset: int = 0):
        self.regex = re.compile(regex)
        self.message = message
        self.offset = offset

    def check(self, module, path, line):
        if search := self.regex.search(line):
            raise exceptions.SingleLineError(self.message, line, search.start() + self.offset)


class LineLength(LineChecker):
    """ Fails if line length is more than 120 characters """
    LIMIT = 120
    # A pipe-table row has to be one line -- there is no continuation syntax to wrap it onto --
    # so the limit is unsatisfiable there without rewording the cell. Volume 28's
    # `truth-or-dare-celestial` tables are 28 such rows, and trimming every scrap of alignment
    # padding would still leave 12 of them over. Exempt the row rather than train authors to
    # ignore the checker.
    re_table_row = re.compile(r'^\s*\|.*\|\s*$')

    def check(self, module, path, line):
        if self.re_table_row.match(line):
            return

        # Lines arrive straight from file iteration, so all but the last still carry their
        # newline. Counting it made the effective limit 119 and flagged every line of exactly
        # 120 characters -- and inconsistently, since a final line without a newline got the
        # full 120.
        if len(line.rstrip('\r\n')) > self.LIMIT:
            raise exceptions.SingleLineError("Line too long", line, self.LIMIT - 1)


class Reference(LineChecker):
    """ Check pandoc reference labels for tables, equations and figures """
    re_reference = re.compile(r'{#(?P<kind>(eq|fig|tbl)):(?P<sub>[^}]+)}')

    def check(self, module, path, line):
        # Only process lines that can be identified as references"
        if match := self.re_reference.search(line):
            log.debug(f"Found reference label {line}")
            match.group('kind')
            sub = match.group('sub')
            match module:
                case 'seminar':
                    # Parse filename structure in `seminar`
                    volume, semester, round, problem = path.parts[-5:-1]
                    file_id = f"{volume}{semester}{round}{problem}"
                    if re.match(fr'{file_id}:[\w]+', sub):
                        logging.debug(f"Correct label in {line}")
                    else:
                        raise exceptions.SingleLineError("Nonconforming label", line, match.start() + 6)
                case 'naboj':
                    # Parse filename structure in `naboj`
                    problem_id = path.parts[5]
                    # Problems should have empty sublabel, solutions named sublabels
                    if (path.stem == 'problem' and re.match(fr'{problem_id}', sub)) or \
                       (path.stem == 'solution' and re.match(fr'{problem_id}:[a-zA-Z0-9_]+', sub)):
                        logging.debug(f"Correct label in {line}")
                    else:
                        raise exceptions.SingleLineError("Invalid label", line, match.start() + 6)
                case _:
                    raise ValueError(f'Unsupported module {module}')


class EqualsSpaces(LineChecker):
    re_equal_spaces = re.compile(r'(?!\\(?:SI|num|si)\[[\w-]+| |\{| &|(#eq:[a-z-]+ )?height)(=|\\approx|\\doteq|\\geq|\\leq|\\gg|\\ll)(?! |\}|& |[\w-]+(,|\])|[0-9]+mm|$)')

    def check(self, module, path, line):
        if match := self.re_equal_spaces.search(line):
            raise exceptions.SingleLineError(f'Spaces missing around "{match.group(0)}"', line, match.end() - 1)


class CdotSpaces:
    re_cdot = re.compile(r'[^ ]\\cdot[^$]')

    def check(self, module, path, line):
        if search := self.re_cdot.search(line):
            raise exceptions.SingleLineError("Spaces missing around \\cdot", line, search.start() + 1)


class PlusSpaces:
    re_plus_in_quotes = re.compile(r'"\+"')
    re_plus_in_curly = re.compile(r'{\+}')
    re_plus_unary = re.compile(r'[(\[]\+[^ ]')
    re_plus_spaces = re.compile(r'[^ ]\+[^ ]')

    re_plus = re.compile(r'(?<! |"|\(|\[|\{|\$)(\+)(?! |"|\)|\]|\})')

    def check(self, module, path, line):
        if search := self.re_plus.search(line):
            raise exceptions.SingleLineError('Spaces missing around "+"', line, search.end() - 2)


class DoubleDollars:
    re_dollars = re.compile(r'\$\$')
    re_dollars_curly_open = re.compile(r'\$\${')
    re_dollars_curly_close = re.compile(r'}\$\$')
    re_only_dollars = re.compile(r'^( *|%)\$\$$')
    re_dollars_ref_missing_space = re.compile(r'\$\${#eq:[a-z0-9-:]+}')
    re_dollars_ref = re.compile(r'^ *\$\$ {#eq:[\w:-]+}$')
    re_aligned_begin = re.compile(r'^\$\$ ?\\begin\{aligned\}')
    re_aligned_end = re.compile(r'^\\end\{aligned\} ?\$\$')
    # A display equation inside a footnote closes as `$$]`, and the sentence the footnote
    # interrupts carries on after it: `$$] teda`. Valid pandoc, so it cannot be "$$ within text".
    # The footnote bracket takes the label's place, so no `{#eq:...}` is possible here.
    re_dollars_footnote = re.compile(r'^ *\$\$\](\s|$)')

    def check(self, module, path, line):
        if search := self.re_dollars_ref_missing_space.search(line):
            raise exceptions.SingleLineError('Reference missing a space', line, search.start() + 4)

        if self.re_only_dollars.match(line) \
            or self.re_dollars_ref.match(line) \
            or self.re_dollars_footnote.match(line) \
            or self.re_dollars_curly_open.match(line) \
            or self.re_dollars_curly_close.match(line):
            return

        if search := self.re_aligned_begin.search(line):
            raise exceptions.SingleLineError('\\begin{aligned} on the same line as $$', line, search.start())

        if search := self.re_aligned_end.search(line):
            raise exceptions.SingleLineError('\\end{aligned} on the same line as $$', line, search.start())

        if search := self.re_dollars.search(line):
            raise exceptions.SingleLineError('Double dollars within text', line, search.start())


class ParenthesesSpace:
    re_right_space = re.compile(r'[^ ] +(\\right)?\)')
    re_left_space = re.compile(r'(\\left)?\( ')

    def check(self, module, path, line):
        if match := self.re_left_space.search(line):
            raise exceptions.SingleLineError("Space after left parenthesis", line, match.start())

        if match := self.re_right_space.search(line):
            raise exceptions.SingleLineError("Space before right parenthesis", line, match.start() + 1)


class Parentheses:
    re_image = re.compile(r'^!\[.*\](.*){.*}$')
    re_left = re.compile(r'(?<!left)\(')
    re_right = re.compile(r'(?<!right)\)')

    def check(self, module, path, line):
        if self.re_image.match(line):
            return

        if search := self.re_left.search(line):
            raise exceptions.SingleLineError("Consider using \\left(", line, search.start())

        if search := self.re_right.search(line):
            raise exceptions.SingleLineError("Consider using \\right)", line, search.start())


class SIExponents:
    re_fail = re.compile(r'(?P<command>\\ang|\\SI|\\SIlist|\\SIrange){[^}]*(\\cdot|\\times|\^)[^}]*}')

    def check(self, module, path, line):
        if search := self.re_fail.search(line):
            raise exceptions.SingleLineError(f"Use e notation instead of TeX inside {search.group('command')}",
                line, search.start() + len(search.group('command')) + 1)

class ConflictMarkers:
    re_fail = re.compile(r'(<<<<<<<|=======|>>>>>>>)')

    def check(self, module, path, line):
        if search := self.re_fail.search(line):
            raise exceptions.SingleLineError("Git conflict markers found!", line, search.start())


class DoubleSpace:
    re_double_space = re.compile(r'.*\w  +\w')

    def check(self, module, path, line):
        if search := self.re_double_space.search(line):
            raise exceptions.SingleLineError('Double spaces', line, search.end())


"""
class LineTooLong(SingleLineChecker):
    def __init__(self):
        super().__init__('Line too long', 120)

    def check(self, module, path, line):
        return len(line) > 120 and line[0] != '@'


def too_long(line):
    if len(line) > 120 and line[0] != '@':
        raise SingleLineError('Line too long', line, 120)


"""

def encoding(filename):
    """
    File-level checks: the whole file must be UTF-8 and must use Unix line endings.

    CRLF is reported here rather than per line because a file that has it usually has it
    everywhere -- 40 of volume 28's translations were wholly CRLF -- and one message per file
    is more use than one per line. It is not cosmetic either: the stray carriage return counts
    towards the line length, so every line in such a file measures one character too long.
    """
    try:
        with codecs.open(filename, encoding='utf-8', errors='strict') as f:
            for line in f:
                pass
    except UnicodeDecodeError:
        raise exceptions.EncodingError(f'{filename} is not a UTF-8 file')

    with open(filename, 'rb') as f:
        if b'\r' in f.read():
            raise exceptions.EncodingError(f'{filename} uses Windows (CRLF) line endings')

    return True
