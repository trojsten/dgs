import re

class SingleLineError(Exception):
    def __init__(self, message, line):
        super(SingleLineError, self).__init__(message)
        self.message    = message
        self.line       = line

class EncodingError(Exception):
    def __init__(self, message, errors):
        super(EncodingError, self).__init__(message)

def doubleDollars(line):
    dollars = re.compile('\$\$')
    onlyDollars = re.compile('^\$\$$')

    return not (dollars.search(line) is not None and not onlyDollars.match(line))
