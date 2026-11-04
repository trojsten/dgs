r"""
`tools/ninja/ink.py` -- the Makefile's colours on Ninja's `description` lines.

Two things can go wrong here and neither shows up as a failed build, which is why they are
pinned: a `{` reaching `str.format` that was meant for the reader, and a line that does not
end in the default colour, which leaves the next one tinted.
"""
import re

import pytest

from tools.ninja import ink

#: What `tput sgr0` writes, with the charset reset `tput` adds for xterm allowed either way.
RE_ESCAPE = re.compile(r'(?:\x1b\(B)?\x1b\[[0-9;]*m')


@pytest.fixture
def coloured(monkeypatch):
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.setenv('TERM', 'xterm-256color')


class TestTheColours:
    def test_a_description_ends_in_the_default(self, coloured):
        """Otherwise the colour of the last thing named bleeds into Ninja's next line."""
        assert ink.described('{a}Copying {f}$in').endswith(ink.PALETTE['d'])

    def test_ninja_s_own_variables_pass_through(self, coloured):
        """`$in` is expanded by Ninja when the edge runs, long after `format` has been."""
        assert '$in' in ink.described('{a}Copying {f}$in')
        assert '$out' in ink.described('{a}to {f}$out')

    def test_the_text_survives_the_colours(self, coloured):
        said = ink.described('{a}[jinja] Rendering {x}$kind template{a} {f}$in')
        assert RE_ESCAPE.sub('', said) == '[jinja] Rendering $kind template $in'

    @pytest.mark.parametrize('environment', [{'NO_COLOR': '1'}, {'TERM': 'dumb'},
                                             {'TERM': ''}])
    def test_a_terminal_that_is_not_one_gets_no_escapes(self, monkeypatch, environment):
        monkeypatch.delenv('NO_COLOR', raising=False)
        monkeypatch.setenv('TERM', 'xterm-256color')
        for key, value in environment.items():
            monkeypatch.setenv(key, value)
        said = ink.described('{a}[jinja] Rendering {x}$kind template{a} {f}$in')
        assert said == '[jinja] Rendering $kind template $in'
        assert '\x1b' not in said


class TestEveryDescriptionInTheGraph:
    """
    Over the rules themselves, because a stray brace in one of them is a `KeyError` at
    generation time and a missing reset is invisible until two lines run together.
    """

    @staticmethod
    def descriptions() -> list[str]:
        import io

        from tools.ninja.generate import rules
        from tools.ninja.writer import Writer

        out = io.StringIO()
        rules(Writer(out))
        return [line.split(' = ', 1)[1]
                for line in out.getvalue().splitlines() if line.startswith('  description = ')]

    def test_there_are_some(self):
        assert len(self.descriptions()) > 15

    def test_each_one_ends_in_the_default(self, coloured):
        for said in self.descriptions():
            assert said.endswith(ink.PALETTE['d']), said

    def test_none_of_them_leaks_a_brace(self):
        """A `{` that `format` did not consume is a marker nobody defined."""
        for said in self.descriptions():
            assert '{' not in said and '}' not in said, said
