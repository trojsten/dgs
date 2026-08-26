#!/usr/bin/env python
import argparse
import io
import logging
import numbers
import pprint
from abc import ABC
from io import TextIOWrapper
from pathlib import Path

from enschema import Or, Schema
from enschema import Optional as Opt

from core import cli, i18n
from core.builder.context.context import RESERVED_NAMES, Context, ValidIdentifier
from core.builder.context.file import FileContext
from core.builder.context.quantities import PhysicsConstant
from core.builder.context.quantities.math import MathObject
from core.builder.jinja import MarkdownJinjaRenderer
from core.utilities import colour as c

log = logging.getLogger('dgs')


class JinjaConvertor:
    """
    Jinja template convertor wrapper.

    Renders a single template to a file, using a provided Context.
    """
    def __init__(self,
                 template_file: TextIOWrapper,
                 context: Context,
                 *,
                 preamble: io.TextIOWrapper | None = None,
                 debug: bool = False):
        """
        Parameters
        ----------
        template_file:
            The Jinja template file to render.
        context:
            The context to use for rendering the template.
        preamble:
            The Jinja preamble file to use (optional). May contain computations.
        debug:
            Activate debug mode.
        """
        self.context: Context = context
        self.preamble: str | None = preamble.read() if preamble else None
        self.template: str = template_file.read()

        if debug:
            log.debug(f"{c.debug('Template to render into')}:")
            print(self.template)
            log.debug(f"{c.debug('Context data')}:")
            pprint.pprint(context.data)

        self.renderer = MarkdownJinjaRenderer()

    def prepare_template(self,
                         template: str) -> str:
        """
        Prepare a template for rendering.

        Currently just prepends the preamble, if available, separated from
        the template by exactly one newline. An empty (or whitespace-only)
        preamble is treated as absent, so no leading blank line is added.
        """
        if self.preamble and self.preamble.strip():
            return self.preamble.rstrip("\n") + "\n" + template
        else:
            return template

    def run(self):
        # First pass: expand all equations and values
        intermediate = self.renderer.render(self.prepare_template(self.template), self.context.data)
        # Second pass: expand all tags within equations
        return self.renderer.render(self.prepare_template(intermediate), self.context.data)


class NameCollisionError(Exception):
    """
    Raised when a `values:` or `derived:` key collides with another name in the same namespace:
    either one of the two the render context holds itself (`const`, `eq`), or a `values` entry that
    a `derived` entry would overwrite. Both are silent otherwise -- whoever is added last wins.
    """
    def __init__(self, key: str, block: str, reason: str):
        super().__init__(f"`{block}` may not define `{key}`: {reason}. Rename it.")
        self.key = key
        self.block = block


class MissingWordError(Exception):
    """
    A word the active language does not define.

    Never a fallback. A word inside maths is prose, and a fallback for prose means a Slovak booklet
    printing `therefore` -- correct-looking output that nobody notices until it is in print. Failing
    the build is the only version of this that gets fixed.
    """
    def __init__(self, term, language, available, where):
        super().__init__(
            f"`{term}` has no {language} translation in {where} "
            f"(it has {', '.join(sorted(available)) or 'none'}). "
            f"Add it there; there is deliberately no fallback."
        )


class LocalisedWords:
    """
    Words resolved on access rather than up front, for one language.

    Up front is wrong: `21/troll-science` writes its equation with translated subscripts in four of
    its six languages and differently in the other two, so resolving everything eagerly would fail a
    Polish build over a word Polish never asks for. Asking is what makes a word required.
    """
    def __init__(self, words, language, where):
        self._words = words
        self._language = language
        self._where = where
        self.where = where

    def __getitem__(self, term):
        per_language = self._words.get(term)
        if per_language is None:
            raise MissingWordError(term, self._language, (), self._where)
        if isinstance(per_language, str):
            # `core/i18n` is already one language per file, so the value is the word itself
            return per_language
        if self._language not in per_language:
            raise MissingWordError(term, self._language, per_language, self._where)
        return per_language[self._language]

    def __contains__(self, term):
        return term in self._words

    def __iter__(self):
        return iter(self._words)

    def keys(self):
        return self._words.keys()


#: Jinja parses these as keywords, so `(§ i18n.and §)` is a syntax error rather than a lookup.
#: Those words are reached with a `w` suffix -- `(§ i18n.andw §)` -- and **only** these need it;
#: every other word is spelled exactly as it appears in `core/i18n/<lang>.yaml`.
JINJA_KEYWORDS = frozenset({
    'and', 'or', 'not', 'if', 'else', 'elif', 'in', 'is', 'for', 'true', 'false', 'none',
})


class LocalisedI18n(dict):
    """
    The locale's data, with its `words:` also reachable directly: `(§ i18n.therefore §)` and
    `(§ i18n.andw §)` rather than `(§ i18n.words['therefore'] §)`.

    The subscript form still works and is what `words` itself is for; this is the spelling a
    source actually wants, because a conjunction inside an equation is read far more often than
    it is written and `i18n.words['and']` puts three kinds of bracket around one word.

    A key that is not part of the locale's own data is looked up as a word, so a missing one
    raises `MissingWordError` naming the term, the language and the file to add it to -- rather
    than resolving to Jinja's `Undefined`, which reports the *tag* and not the word.
    """
    def __init__(self, data: dict, words: 'LocalisedWords'):
        super().__init__(data)
        collisions = sorted(set(words.keys()) & set(data.keys()))
        if collisions:
            raise ValueError(
                f"Word{'s' if len(collisions) > 1 else ''} {', '.join(collisions)} in "
                f"{words.where} collide{'' if len(collisions) > 1 else 's'} with a locale key of "
                f"the same name, so `i18n.{collisions[0]}` would silently return the locale's "
                f"value instead of the word. Rename the word."
            )
        self._words = words

    def __missing__(self, key: str):
        term = key[:-1] if key.endswith('w') and key[:-1] in JINJA_KEYWORDS else key
        return self._words[term]


class DerivedQuantityError(Exception):
    """
    Raised when a `derived:` expression cannot be evaluated. Names it, so the author does not have to
    guess which of a dozen expressions is broken -- the underlying error alone rarely says.
    """
    def __init__(self, key: str, expression: str, cause: Exception):
        super().__init__(f"Could not evaluate derived quantity `{key}`: {expression!r}\n"
                         f"    {cause.__class__.__name__}: {cause}")
        self.key = key
        self.expression = expression
        self.cause = cause


class ConstantsContext(FileContext):
    _schema = Schema({
        str: PhysicsConstant,
    })

    def __init__(self, new_id: str, path: Path, **defaults):
        super().__init__(new_id, path, **defaults)
        self.add(**{
            alias: PhysicsConstant.construct(name, **data)
            for name, data in self.data.items()             # Create and add all defined constants
            for alias in [name] + data.get('aliases', [])   # Also include under all available aliases for them
        })


class StandaloneContext(FileContext):
    """
    Base context for the standalone Markdown renderer
    (in the "source (Markdown / Jinja) -> render (Markdown) -> build (TeX / HTML) -> output (TeX / HTML)" chain)
    """
    # All three blocks name things, so they share one identifier rule (`ValidIdentifier`).
    # `eq` used to demand `^[a-z][a-zA-Z0-9_]+$`, which uniquely rejected capitals and
    # single-character names -- `eq: {v: ...}` was invalid while `derived: {v: ...}` was fine.
    _schema = Schema({
        'id': str,
        Opt('values'): dict[ValidIdentifier, Or(str, float, int, PhysicsConstant)],  # Values
        # Quantities computed from `values` and `const`: name -> Jinja expression.
        # Evaluated in document order, so an entry may use anything defined above it.
        Opt('derived'): dict[ValidIdentifier, str],
        Opt('eq'): dict[ValidIdentifier, str],
        # A word that has to be translated but belongs to this problem alone: term -> language ->
        # text, reached as `(§ w.air §)`. The recurring ones (`and`, `or`) live in `core/i18n`
        # instead; these are the one-offs, and 167 of the 190 words found inside `\text{}` in phys
        # appear in exactly one problem.
        Opt('words'): dict[ValidIdentifier, dict[str, str]],
    })


class CLIInterface(cli.CLIInterface, ABC):
    """
    Jinja standalone convertor CLI interface
    """
    description = "Jinja convertor"
    context_cls = StandaloneContext

    @staticmethod
    def _reject_name_collisions(block: dict, block_name: str, *, taken: set[str] = frozenset()) -> None:
        """
        Refuse names that would silently replace something already in the context. `values` and
        `derived` are spread into one namespace shared with `const` and `eq`, and whoever is added
        last wins, so a clash is invisible until a formula quietly uses the wrong thing.
        """
        for key in block:
            if key in RESERVED_NAMES:
                raise NameCollisionError(key, block_name, "it is used by the rendering context")
            if key in taken:
                raise NameCollisionError(key, block_name, "it is already defined under `values`")

    def build_context(self) -> Context:
        context = self.context_cls(
            self.args.context.name,
            Path(self.args.context.name)
        ).add(id=Path(self.args.context.name).parent.name)      # Also add the problem id here
        context.validate()
        constants = ConstantsContext('constants', Path('core/data/constants.yaml'))
        constants.validate()

        ctx = Context('cont')

        # Process values: if a PhysicsConstant can be constructed, do so, and add directly to the context
        if 'values' in context.data:
            values = context.data['values']
            self._reject_name_collisions(values, 'values')

            for key, params in values.items():
                if isinstance(params, dict):
                    symbol = params.pop('symbol', key)
                    values[key] = PhysicsConstant.construct(key, symbol=symbol, **params)
                elif isinstance(params, (str, numbers.Number)):
                    values[key] = params
                else:
                    raise TypeError(f"Unsupported type {type(params)} ({params})")

            ctx.add(**values)

        # Constants must be present before `derived` expressions are evaluated, as they use `const.x`
        ctx.adopt(const=constants)

        # The active language, so a template can reach a translated word. The Markdown stage used to
        # parse `locale` and drop it -- only the convertor knew which language it was rendering, so
        # no source could say `and` in nine languages without writing it out nine times.
        locale = i18n.languages[self.args.locale]
        localised = locale.as_dict()
        # wrapped so a word this language does not define stops the build with a message naming it,
        # rather than resolving to something plausible in the wrong language
        words = LocalisedWords(localised.get('words') or {}, self.args.locale,
                               f'core/i18n/{self.args.locale}.yaml')
        # Reachable both ways: `i18n.words['and']` and, since a conjunction inside an equation is
        # read far more often than written, `i18n.andw` -- see `LocalisedI18n`.
        localised = LocalisedI18n(localised, words)
        localised['words'] = words
        ctx.add(i18n=localised)

        # This problem's own words, resolved when a template asks for one.
        #
        # No collision check, unlike `values` and `derived`: those land in the top-level namespace
        # where a key called `const` would shadow the constants, while a word is reached as
        # `words.const` and shadows nothing. `22/ht-conundrum` wants exactly that name -- its
        # equations end in `= const` -- and refusing it would be a rule enforcing nothing.
        if 'words' in context.data:
            ctx.add(words=LocalisedWords(context.data['words'], self.args.locale,
                                         "this problem's meta.yaml"))

        # Process derived quantities: evaluate the expressions in document order, adding each result
        # to the context, so that a later expression may build on an earlier one. This replaces the
        # old `preamble.md` full of `@J set` lines for everything but genuine control flow.
        if 'derived' in context.data:
            self._reject_name_collisions(context.data['derived'], 'derived',
                                         taken=set(context.data.get('values') or {}))
            renderer = MarkdownJinjaRenderer()
            for key, expression in context.data['derived'].items():
                try:
                    ctx.add(**{key: renderer.evaluate(expression, ctx.data)})
                except Exception as e:
                    raise DerivedQuantityError(key, expression, e) from e

        # Process all equations: create MathObject and store under the `eq` key in the context
        if 'eq' in context.data:
            for idx, fragment in context.data['eq'].items():
                context.data['eq'][idx] = MathObject(f"{context.data['id']}:{idx}", fragment)
            ctx.add(eq=context.data['eq'])

        return ctx

    def build_convertor(self, args, **kwargs):
        if self.args.preamble is not None:
            if not Path(self.args.preamble).exists():
                log.error(f"Preamble file {Path(self.args.preamble)} specified but not found")
            preamble = open(self.args.preamble, 'r')
        else:
            preamble = None

        return JinjaConvertor(self.args.infile,
                              self.build_context(),
                              preamble=preamble,
                              debug=self.args.debug)

    def add_extra_arguments(self):
        self.parser.add_argument('-C', '--context', type=argparse.FileType('r'))
        self.parser.add_argument('-P', '--preamble', type=str)
