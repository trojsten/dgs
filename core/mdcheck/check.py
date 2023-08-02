from abc import ABCMeta, abstractmethod
import re
import codecs

from mdcheck import exceptions


class LineChecker(metaclass=ABCMeta):
    @abstractmethod
    def check(self, line):
        pass


class FailIfFound(LineChecker):
    def __init__(self, regex, message, *, offset=0):
        self.regex = re.compile(regex)
        self.message = message
        self.offset = offset

    def check(self, line):
        if search := self.regex.search(line):
            raise exceptions.SingleLineError(self.message, line, search.start() + self.offset)


class LineLength(LineChecker):
    def check(self, line):
        if len(line) > 120:
            raise exceptions.SingleLineError("Line too long", line, 119)


class EqualsSpaces():
    re_equal_spaces = re.compile(r'(?!\\(?:SI|num|si)\[[\w-]+| |\{| &|(#eq:[a-z-]+ )?height)(=|\\approx|\\doteq|\\geq|\\leq|\\gg|\\ll)(?! |\}|& |[\w-]+(,|\])|[0-9]+mm|$)')

    def check(self, line):
        if search := self.re_equal_spaces.search(line):
            raise exceptions.SingleLineError(f'Spaces missing around "{search.group(0)}"', line, search.end() - 1)


class CdotSpaces():
    re_cdot = re.compile(r'[^ ]\\cdot[^$]')

    def check(self, line):
        if search := self.re_cdot.search(line):
            raise exceptions.SingleLineError("Spaces missing around \\cdot", line, search.start() + 1)


class PlusSpaces():
    re_plus_in_quotes = re.compile(r'"\+"')
    re_plus_in_curly = re.compile(r'{\+}')
    re_plus_unary = re.compile(r'[(\[]\+[^ ]')
    re_plus_spaces = re.compile(r'[^ ]\+[^ ]')

    re_plus = re.compile('(?<! |"|\(|\[|\{|\$)(\+)(?! |"|\)|\]|\})')

    def check(self, line):
        if search := self.re_plus.search(line):
            raise exceptions.SingleLineError('Spaces missing around "+"', line, search.end() - 2)


class DoubleDollars():
    re_dollars = re.compile(r'\$\$')
    re_dollars_curly_open = re.compile(r'\$\${')
    re_dollars_curly_close = re.compile(r'}\$\$')
    re_only_dollars = re.compile(r'^( *|%)\$\$$')
    re_dollars_ref_missing_space = re.compile(r'\$\${#eq:[a-z0-9-:]+}')
    re_dollars_ref = re.compile(r'^ *\$\$ {#eq:[\w:-]+}$')
    re_aligned_begin = re.compile(r'^\$\$ ?\\begin\{aligned\}')
    re_aligned_end = re.compile(r'^\\end\{aligned\} ?\$\$')

    def check(self, line):
        if search := self.re_dollars_ref_missing_space.search(line):
            raise exceptions.SingleLineError('Reference missing a space', line, search.start() + 4)

        if self.re_only_dollars.match(line) \
            or self.re_dollars_ref.match(line) \
            or self.re_dollars_curly_open.match(line) \
            or self.re_dollars_curly_close.match(line):
            return

        if search := self.re_aligned_begin.search(line):
            raise exceptions.SingleLineError('\\begin{aligned} on the same line as $$', line, search.start())

        if search := self.re_aligned_end.search(line):
            raise exceptions.SingleLineError('\\end{aligned} on the same line as $$', line, search.start())

        if search := self.re_dollars.search(line):
            raise exceptions.SingleLineError('Double dollars within text', line, search.start())


class ParenthesesSpace():
    re_right_space = re.compile(r'[^ ] +(\\right)?\)')
    re_left_space = re.compile(r'(\\left)?\( ')

    def check(self, line):
        if search := self.re_left_space.search(line):
            raise exceptions.SingleLineError("Space after left parenthesis", line, search.start())

        if search := self.re_right_space.search(line):
            raise exceptions.SingleLineError("Space before right parenthesis", line, search.start() + 1)


class Parentheses():
    re_image = re.compile(r'^!\[.*\](.*){.*}$')
    re_left = re.compile(r'(?<!left)\(')
    re_right = re.compile(r'(?<!right)\)')

    def check(self, line):
        if self.re_image.match(line):
            return

        if search := self.re_left.search(line):
            raise exceptions.SingleLineError("Consider using \\left(", line, search.start())

        if search := self.re_right.search(line):
            raise exceptions.SingleLineError("Consider using \\right)", line, search.start())


class CommaSpace():
    re_fail = re.compile(r',[^\s^]')

    def check(self, line):
        if search := self.re_fail.search(line):
            raise exceptions.SingleLineError("Comma not followed by whitespace", line, search.start())


class SemicolonSpace():
    re_fail = re.compile(r'(?!\\ang{);[^\s]')

    def check(self, line):
        if search := self.re_fail.search(line):
            raise exceptions.SingleLineError("Semicolon not followed by whitespace", line, search.start())


class SIExponents():
    re_fail = re.compile(r'(?P<command>\\ang|\\SI|\\SIlist|\\SIrange){[^}]*(\\cdot|\\times|\^)[^}]*}')

    def check(self, line):
        if search := self.re_fail.search(line):
            raise exceptions.SingleLineError(f"Use e notation instead of TeX inside {search.group('command')}",
                line, search.start() + len(search.group('command')) + 1)

class ConflictMarkers():
    re_fail = re.compile(r'(<<<<<<<|=======|>>>>>>>)')

    def check(self, line):
        if search := self.re_fail.search(line):
            raise exceptions.SingleLineError(f"Git conflict markers found!", line, search.start())


class DoubleSpace():
    re_double_space = re.compile('.*\w  +\w')

    def check(self, line):
        if search := self.re_double_space.search(line):
            raise exceptions.SingleLineError('Double spaces', line, search.end())


class EquationReference():
    def check(self, line):
        return True


"""
class LineTooLong(SingleLineChecker):
    def __init__(self):
        super().__init__('Line too long', 120)

    def check(self, line):
        return len(line) > 120 and line[0] != '@'


def too_long(line):
    if len(line) > 120 and line[0] != '@':
        raise SingleLineError('Line too long', line, 120)


"""

def encoding(filename):
    try:
        f = codecs.open(filename, encoding='utf-8', errors='strict')
        for line in f:
            pass
        return True
    except UnicodeDecodeError:
        raise exceptions.EncodingError(f'{filename} is not a UTF-8 file')

