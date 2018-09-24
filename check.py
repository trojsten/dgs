import re, codecs

class SingleLineError(Exception):
    def __init__(self, message, line, column):
        super(SingleLineError, self).__init__(message)
        self.message    = message
        self.line       = line
        self.column     = column

class EncodingError(Exception):
    def __init__(self, message):
        super(EncodingError, self).__init__(message)
        self.message    = message

def doubleDollars(line):
    dollars = re.compile('\$\$')
    onlyDollars = re.compile('^\$\$ *$')
    
    search = dollars.search(line)
    only = onlyDollars.match(line)

    if (search is not None and not only):
        raise SingleLineError('Double dollars within text', line, search)

def tooLong(line):
    if len(line) > 200:
        raise SingleLineError('Line too long', line, len(line))

def trailingWhitespace(line):
    bad = re.compile('[ \t]+$')
    position = bad.search(line)

    if position is not None:
        raise SingleLineError('Trailing whitespace', line, len(line))


def encoding(filename):
    try:
        f = codecs.open(filename, encoding = 'utf-8', errors = 'strict')
        for line in f:
            pass
        return True 
    except UnicodeDecodeError:
        raise EncodingError('Not a UTF-8 file')

