import re


class Locale:
    def __init__(self, name, locale, quotes, **extras):
        self.name = name
        self.locale = locale
        self.quotes = quotes

        for k, v in extras.items():
            self.__setattr__(k, v)


class RegexFailure:
    def __init__(self, pattern: str, *, error: str, flags: re.RegexFlag = re.NOFLAG):
        self.pattern = re.compile(pattern, flags=flags)
        self.error = error


class RegexReplacement:
    def __init__(self, pattern: str, repl: str, *, purpose: str = "", flags: re.RegexFlag = re.NOFLAG):
        assert isinstance(flags, re.RegexFlag) or flags is None, f"Flags {flags} is not a re.RegexFlag"

        self.pattern = re.compile(pattern, flags=flags)
        self.repl = repl
        self.purpose = purpose
