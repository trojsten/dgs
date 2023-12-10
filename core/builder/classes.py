import re


class RegexFailure:
    def __init__(self, pattern: str, *, error: str, flags: re.RegexFlag = re.NOFLAG):
        self.pattern = re.compile(pattern, flags=flags)
        self.error = error


class RegexReplacement:
    def __init__(self, pattern: str, repl: str, *, purpose: str = "", flags: re.RegexFlag = re.NOFLAG):
        assert isinstance(flags, re.RegexFlag) or flags is None, \
            f"Flags {flags} should be a re.RegexFlag but is {flags.__class__}"

        self.pattern = re.compile(pattern, flags=flags)
        self.repl = repl
        self.purpose = purpose
