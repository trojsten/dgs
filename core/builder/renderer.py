#!/usr/bin/env python
import argparse
import io
import numbers
import pprint
import logging

from abc import ABC
from io import TextIOWrapper

from pathlib import Path
from typing import Optional

from enschema import Schema, Optional as Opt, Or

from core import cli
from core.builder.context.context import Context
from core.builder.context.file import FileContext
from core.builder.context.quantities.math import MathObject
from core.builder.jinja import MarkdownJinjaRenderer

from core.builder.context.quantities import PhysicsConstant
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
                 preamble: Optional[io.TextIOWrapper] = None,
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
        self.preamble: Optional[str] = preamble.read() if preamble else None
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

        Currently just prepends the preamble, if available
        """
        return (self.preamble or "") + template

    def run(self):
        # First pass: expand all equations and values
        intermediate = self.renderer.render(self.prepare_template(self.template), self.context.data)
        # Second pass: expand all tags within equations
        return self.renderer.render(self.prepare_template(intermediate), self.context.data)


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
    _schema = Schema({
        'id': str,
        Opt('values'): dict[str, Or(str, float, int, PhysicsConstant)],  # Values
        Opt('eq'): dict[str, str],                  # Equations
    })



class CLIInterface(cli.CLIInterface, ABC):
    """
    Jinja standalone convertor CLI interface
    """
    description = "Jinja convertor"
    context_cls = StandaloneContext

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

            for key, params in values.items():
                if isinstance(params, dict):
                    symbol = params.pop('symbol', key)
                    values[key] = PhysicsConstant.construct(key, symbol=symbol, **params)
                elif isinstance(params, str) or isinstance(params, numbers.Number):
                    values[key] = params
                else:
                    raise TypeError(f"Unsupported type {type(params)} ({params})")

            ctx.add(**values)

        # Process all equations: create MathObject and store under the `eq` key in the context
        if 'eq' in context.data:
            for idx, fragment in context.data['eq'].items():
                context.data['eq'][idx] = MathObject(f"{context.data['id']}:{idx}", fragment)
            ctx.add(eq=context.data['eq'])

        ctx.adopt(const=constants)
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