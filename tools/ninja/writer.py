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
import textwrap


def escape_path(word: str) -> str:
    return word.replace('$ ', '$$ ').replace(' ', '$ ').replace(':', '$:')


def escape(value: str) -> str:
    return value.replace('$', '$$')


class Writer:
    def __init__(self, out, width: int = 100):
        self.out = out
        self.width = width
        #: Every output written so far, to the edge that wrote it. Ninja refuses two rules for
        #: one output -- `multiple rules generate …` -- and it is right to: make resolved the
        #: same ambiguity silently by taking whichever rule it saw last, which is how
        #: `Makefile:377` and `:397` came to be the same rule head with the second unreachable.
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
            self.variable(key, value, 1)
        return outputs


    def has(self, output: str) -> bool:
        """Whether something already produces this path."""
        return escape_path(str(output)) in self.emitted


def _listify(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return sorted(value) if isinstance(value, set) else list(value)
    return [value]
