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


class LocalisedWords:
    """
    A problem's `words:` resolved on access rather than up front.

    Up front is wrong: `21/troll-science` writes the equation with translated subscripts in four of
    its six languages and differently in the other two, so resolving everything eagerly would fail a
    Polish build over a word Polish never asks for. Access is what makes a word required.
    """
    def __init__(self, words, language):
        self._words = words
        self._language = language

    def __getitem__(self, term):
        try:
            per_language = self._words[term]
        except KeyError:
            raise KeyError(f"no `words.{term}` in this problem's meta.yaml") from None
        if self._language not in per_language:
            raise MissingWordError(term, self._language, per_language)
        return per_language[self._language]

    def __contains__(self, term):
        return term in self._words

    def __iter__(self):
        return iter(self._words)

    def keys(self):
        return self._words.keys()


class MissingWordError(Exception):
    """A `words:` term the active language does not translate."""
    def __init__(self, term, language, available):
        super().__init__(
            f"`words.{term}` has no {language} translation "
            f"(it has {', '.join(sorted(available)) or 'none'}). "
            f"A problem's own words must cover every language the problem is written in; "
            f"for a word that recurs, use `core/i18n` and `(§ i18n.words[...] §)` instead."
        )


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
        ctx.add(i18n=locale.as_dict())

        # This problem's own words, resolved when a template asks for one
        if 'words' in context.data:
            self._reject_name_collisions(context.data['words'], 'words',
                                         taken=set(context.data.get('values') or {}))
            ctx.add(w=LocalisedWords(context.data['words'], self.args.locale))

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
