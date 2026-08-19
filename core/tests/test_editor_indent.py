"""
The editor's Tab handling, tested through its own JavaScript.

`indentEdit` in `tools/editor/static/app.js` is written as a pure function -- value and selection in,
replacement span and new selection out -- precisely so it can be checked without a browser. The
function is lifted out of the file and run under QuickJS, so this tests the shipped code rather than a
Python transcription of it.

Skipped when `quickjs` is not installed: it is not a project dependency, and a skipped test is worth
more than no test. It has already earned its place -- it caught Tab replacing a selected sentence
with spaces, which in a repository of authored prose is a way to lose a sentence to a stray keystroke.
"""
import json
import pathlib
import re

import pytest

quickjs = pytest.importorskip('quickjs')

APP_JS = pathlib.Path('tools/editor/static/app.js')

#: name, value, selection, indent width, outdenting, expected value, expected selection
CASES = [
    ('a caret inserts up to the next tab stop',
     'abc', 0, 0, 4, False, '    abc', (4, 4)),
    ('mid-word it goes to the stop, not four further',
     'ab', 2, 2, 4, False, 'ab  ', (4, 4)),
    ('on a stop it inserts a whole one',
     '    x', 4, 4, 4, False, '        x', (8, 8)),
    ('YAML indents by two',
     'eq:', 3, 3, 2, False, 'eq: ', (4, 4)),
    ('a selection within one line indents the line and is not eaten',
     'abcdef', 1, 3, 4, False, '    abcdef', (5, 7)),
    ('a selection across lines indents each of them',
     'one\ntwo', 0, 7, 4, False, '    one\n    two', (4, 15)),
    ('a blank line gains nothing, so no trailing whitespace is invented',
     'one\n\ntwo', 0, 8, 4, False, '    one\n\n    two', (4, 16)),
    ('shift-tab outdents each selected line',
     '    one\n    two', 4, 15, 4, True, 'one\ntwo', (0, 7)),
    ('shift-tab removes only the spaces that are there',
     '  one\n    two', 2, 13, 4, True, 'one\ntwo', (0, 7)),
    ('shift-tab with no selection outdents the line the caret is on',
     '    one\nsecond', 6, 6, 4, True, 'one\nsecond', (2, 2)),
    ('shift-tab on an unindented line changes nothing',
     'one\ntwo', 1, 1, 4, True, 'one\ntwo', (1, 1)),
    ('the last line indents even without a trailing newline',
     'a\nb', 2, 3, 4, False, 'a\n    b', (6, 7)),
]


@pytest.fixture(scope='module')
def indent_edit():
    """`indentEdit`, lifted out of app.js and callable from Python."""
    source = APP_JS.read_text()
    match = re.search(r'function indentEdit\(.*?\n\}\n', source, re.S)
    assert match, "indentEdit is no longer a top-level function in app.js"
    context = quickjs.Context()
    context.eval(match.group(0))
    context.eval("""
        function edit(value, s, e, width, outdent) {
            var r = indentEdit(value, s, e, width, outdent);
            return JSON.stringify([value.slice(0, r.from) + r.text + value.slice(r.to),
                                   r.selStart, r.selEnd]);
        }
    """)

    def call(value, start, end, width, outdent):
        got = json.loads(context.eval('edit')(value, start, end, width, outdent))
        return got[0], (got[1], got[2])
    return call


@pytest.mark.parametrize('name,value,start,end,width,outdent,expected,selection',
                         CASES, ids=[c[0] for c in CASES])
def test_indent(indent_edit, name, value, start, end, width, outdent, expected, selection):
    assert indent_edit(value, start, end, width, outdent) == (expected, selection)


def test_tab_never_deletes_text(indent_edit):
    """
    The property behind the fifth case, over every selection of a one-line buffer: Tab may add
    spaces, never remove a character. Outdenting is the only thing allowed to take anything away.
    """
    value = 'a b c'
    for start in range(len(value) + 1):
        for end in range(start, len(value) + 1):
            result, _ = indent_edit(value, start, end, 4, False)
            assert result.replace(' ', '') == value.replace(' ', ''), (start, end, result)
