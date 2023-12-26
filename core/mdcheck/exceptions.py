class SingleLineError(Exception):
    def __init__(self, message, line, column):
        super().__init__(message)
        self.message    = message
        self.line       = line
        self.column     = column


class SingleLineWarning(Exception):
    def __init__(self, message, line, column):
        super().__init__(message)
        self.message    = message
        self.line       = line
        self.column     = column


class EncodingError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message    = message


class MarkdownError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

