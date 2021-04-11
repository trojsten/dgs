import re
import codecs

from mdcheck import exceptions

re_double_space = re.compile('.*\w  +\w')

re_dollars = re.compile('\$\$')
re_only_dollars = re.compile('^ *\$\$$')
re_dollars_ref_missing_space = re.compile('\$\${#eq:[a-z0-9-]+}')
re_dollars_ref = re.compile('^ *\$\$ {#eq:[A-Za-z0-9-]+}$')
re_aligned_begin = re.compile('^\$\$ ?\\\\begin\{aligned\}')
re_aligned_end = re.compile('^\\\\end\{aligned\} ?\$\$')


class LineChecker():
    def check(self, line):
        for checker in [Circ, Tabs, FracWithoutBrace]:
            checker().check(line)


class FailOnSearch():
    def __init__(self, regex, message, *, offset=0):
        self.regex = re.compile(regex)
        self.message = message
        self.offset = offset

    def check(self, line):
        if search := self.regex.search(line):
            raise exceptions.SingleLineError(self.message, line, search.start() + self.offset)


class LineLength():
    def check(self, line):
        if len(line) > 120 and line[0] != '@':
            raise exceptions.SingleLineError("Line too long", line, 119)


class EqualsSpaces():
    re_equal_spaces = re.compile('(?!\\\\(?:SI|num|si)\[[\w-]+| | &)=(?! |& |[\w-]+(,|\]))')

    def check(self, line):
        if search := self.re_equal_spaces.search(line):
            raise exceptions.SingleLineError('Spaces missing around "="', line, search.end() - 1)


class DoubleDollars():
    re_dollars = re.compile('\$\$')
    re_only_dollars = re.compile('^ *\$\$$')
    re_dollars_ref_missing_space = re.compile('\$\${#eq:[a-z0-9-]+}')
    re_dollars_ref = re.compile('^ *\$\$ {#eq:[\w-]+}$')
    re_aligned_begin = re.compile('^\$\$ ?\\\\begin\{aligned\}')
    re_aligned_end = re.compile('^\\\\end\{aligned\} ?\$\$')

    def check(self, line):
        if search := self.re_dollars_ref_missing_space.search(line):
            raise exceptions.SingleLineError('Reference missing a space', line, search.start() + 4)

        if self.re_only_dollars.match(line) or self.re_dollars_ref.match(line):
            return

        if search := self.re_aligned_begin.search(line):
            raise exceptions.SingleLineError('\\begin{aligned} on the same line as $$', line, search.start())

        if search := self.re_aligned_end.search(line):
            raise exceptions.SingleLineError('\\end{aligned} on the same line as $$', line, search.start())

        if search := self.re_dollars.search(line):
            raise exceptions.SingleLineError('Double dollars within text', line, search.start())











def double_space(line):
    if search := re_double_space.search(line):
        raise SingleLineError('Double spaces', line, search.end())


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
        raise EncodingError('Not a UTF-8 file')

