r"""
Reading the old Náboj TeX, one brace at a time.

Everything here exists because a regular expression is the wrong tool for this input. A problem
body contains `{}` of its own, `$$…$$` displays, `%`-to-end-of-line comments and arguments like
`\unit{kJ\,kg^{-1}}` that nest a brace inside a brace. `\zadanie\{(.*?)\}` truncates that at the
first `}` and takes the rest of the problem with it.
"""
import re

#: A `%` that is not `\%`. TeX drops everything after it, including the newline.
RE_COMMENT = re.compile(r'(?<!\\)%[^\n]*\n?')


def strip_comments(text: str) -> str:
    r"""
    Drop `%`-to-end-of-line, which is how these files carry both notes and line-joins.

    The trailing newline goes too, because that is what TeX does: `\obrazok{1}{f.eps}%` followed
    by `}` is one line to TeX, and keeping the newline would put a paragraph break in the middle
    of a sentence.
    """
    return RE_COMMENT.sub('', text.replace('\r\n', '\n').replace('\r', '\n'))


def match_brace(text: str, start: int) -> int:
    r"""
    Index just past the `}` closing the `{` at `start`. Raises if it never closes.

    Counts `\{` and `\}` as ordinary characters rather than delimiters, which they are.
    """
    if start >= len(text) or text[start] != '{':
        raise ValueError(f'no brace group at offset {start}: {text[start:start + 20]!r}')
    depth, i = 0, start
    while i < len(text):
        c = text[i]
        if c == '\\':
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if not depth:
                return i + 1
        i += 1
    raise ValueError(f'unclosed brace group at offset {start}')


def arguments(text: str, start: int, count: int) -> tuple[list[str], int]:
    r"""
    Read `count` consecutive brace groups from `start`, skipping whitespace between them.

    Returns the bodies and the index just past the last one. TeX skips whitespace when looking
    for an argument, and these sources rely on it: `\obrazok {1} {f.eps}` occurs.
    """
    bodies, i = [], start
    for _ in range(count):
        while i < len(text) and text[i] in ' \t\n':
            i += 1
        end = match_brace(text, i)
        bodies.append(text[i + 1:end - 1])
        i = end
    return bodies, i


def macro_body(text: str, name: str) -> str | None:
    r"""
    The body of the first `\name{…}` in `text`, or None if there is none.

    This is how a problem's three parts come out: `\zadanie`, `\vzorak` and `\comment`.
    """
    for m in re.finditer(r'\\' + name + r'(?![a-zA-Z])', text):
        i = m.end()
        while i < len(text) and text[i] in ' \t\n':
            i += 1
        if i < len(text) and text[i] == '{':
            return text[i + 1:match_brace(text, i) - 1]
    return None


def calls(text: str, name: str, arity: int):
    r"""
    Every `\name` with its `arity` arguments, as (start, end, [args]).

    Yielded in source order and with real offsets, so a caller can rewrite the text in place by
    walking the list backwards.
    """
    for m in re.finditer(r'\\' + name + r'(?![a-zA-Z])', text):
        try:
            args, end = arguments(text, m.end(), arity)
        except ValueError:
            continue
        yield m.start(), end, args
