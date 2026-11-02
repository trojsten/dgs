r"""
The Makefile's colours, for Ninja's `description` lines.

Every recipe in `Makefile` opened with an `@echo -e` in four colours -- a blue sentence, the
file names in magenta, the format names in bold green -- and Ninja prints a rule's
`description` where make printed that echo, so the same sentences belong there. They are
written with `{a}`, `{f}`, `{x}` and `{d}` markers and passed through `described`:

    described('{a}[jinja] Rendering {x}Markdown template{a} {f}$in{a} to {f}$out')

`$in` and `$out` are Ninja's, expanded when the edge runs; the braces are Python's, expanded
when the graph is written. The two never meet, which is why one string can carry both.

**Plain SGR rather than `tput`.** The Makefile asked terminfo at parse time -- `$(shell tput
sgr0; tput bold; tput setaf 4)` -- which costs six subprocesses and, more to the point, gives
a different answer depending on `TERM` in the shell that happened to run `make`. The generator
is itself usually run *by* Ninja, where there is no terminal at all, so terminfo would answer
for nothing. These are the codes `tput` emits for every terminal this repository is built on,
minus the `\033(B` charset reset, which does nothing on a UTF-8 terminal.

Colour is baked into `build.ninja` when it is generated, so `NO_COLOR` takes effect at the next
regeneration rather than the next build. Ninja 1.13's status line elides the *visible* text and
re-emits the escapes around it, so a long description truncated to the terminal's width still
ends in the right colour.
"""
import os

#: `c_error` and `c_special` from the Makefile are deliberately absent. The first coloured its
#: three `Incorrect fall-through rule called on …` recipes, which exist because a pattern rule
#: can silently fail to apply -- the defect this build does not have, since a target either has
#: an edge or Ninja says `unknown target`. The second was defined and never used.
PALETTE = {
    'a': '\033[0m\033[1m\033[34m',      # the sentence
    'f': '\033[0m\033[35m',             # a file name
    'x': '\033[0m\033[1m\033[32m',      # a format, or the kind of thing being built
    'd': '\033[0m\033[37m',             # back to the default, which every line ends in
}
PLAIN = dict.fromkeys(PALETTE, '')


def palette() -> dict[str, str]:
    """Honours `NO_COLOR`, and `TERM=dumb`, which is what a terminal says when it is not one."""
    if os.environ.get('NO_COLOR') or os.environ.get('TERM', '') in ('', 'dumb'):
        return PLAIN
    return PALETTE


def described(sentence: str) -> str:
    """One `description`, coloured, ending in the default so nothing bleeds into the next."""
    return sentence.format(**palette()) + palette()['d']
