#!/usr/bin/env python
import argparse
import io
import numbers
import pprint
import shutil
import logging

from abc import ABC
from io import TextIOWrapper, StringIO

from pathlib import Path
from tempfile import SpooledTemporaryFile, NamedTemporaryFile
from typing import Optional

from enschema import Schema, Or, Optional as Opt, And

from core import cli
from core.builder.context.context import Context
from core.builder.context.file import FileContext
from core.builder.jinja import MarkdownJinjaRenderer

from core.builder.context.constant import PhysicsConstant
from core.utilities import colour as c

log = logging.getLogger('dgs')


VALID_TAGS: dict[str, str] = {
    'kinematics': 'kinematics',
    'statics': 'statics',
    'electrostatics': 'electrostatics',
    'nuclear': 'nuclear physics',
    'relativity': 'special or general relativity',
    'uam': 'uniformly accelerated motion',
    'com': 'centre of mass',
    'creative': 'a problem that requires out-of-the-box thinking',
    'thermodynamics': 'thermodynamics',
    'buoyancy': 'buoyancy',
    'troll': 'a problem with a trivial solution',
    'elegant': 'short but interesting problem',
}


def valid_tag(tag: str) -> bool:
    return tag in VALID_TAGS


class JinjaConvertor:
    def __init__(self,
                 template: TextIOWrapper,
                 outfile: Optional[TextIOWrapper],
                 *,
                 context: Context,
                 preamble: Optional[io.TextIOWrapper] = None,
                 preamble_prepend: Optional[str] = '',
                 debug: bool = False):
        self.outfile: Optional[Path] = outfile
        self.context: Context = context

        self.tmp = SpooledTemporaryFile(mode="w+")

        # If there is a preamble, prepend it to the actual file
        if preamble is not None:
            # FixME prepend preamble_prepend to every line (default '@J set ')
            shutil.copyfileobj(preamble, self.tmp)

        # Always copy the actual template
        shutil.copyfileobj(template, self.tmp)
        self.tmp.seek(0)

        if debug:
            log.debug(f"{c.debug('Template to render into')}:")
            print(self.tmp.read())
            self.tmp.seek(0)

            log.debug(f"{c.debug('Context data')}:")
            pprint.pprint(context.data)

        self.renderer = MarkdownJinjaRenderer(template=self.tmp.read())

    def run(self):
        print(self.renderer.render_in_memory(self.context.data), file=self.outfile)
        self.tmp.close()
        return 0


class ConstantsContext(FileContext):
    _schema = Schema({
        str: PhysicsConstant,
    })

    def __init__(self, new_id: str, path: Path, **defaults):
        super().__init__(new_id, path, **defaults)
        self.add(**{
            alias: PhysicsConstant.construct(name, **data)
            for name, data in self.data.items()  # Create and add all defined constants
            for alias in [name] + data.get('aliases', [])  # Also include all available aliases for them
        })


class StandaloneContext(FileContext):
    _schema = Schema({
        'authors': list[str],
        'tags': list[And(str, valid_tag)],
        Opt('values'): dict[str, PhysicsConstant],
    })


class CLIInterface(cli.CLIInterface, ABC):
    """
    Jinja CLI interface
    """
    description = "DeGeŠ Jinja convertor"

    def build_context(self) -> Context:
        context = StandaloneContext(self.args.context.name, Path(self.args.context.name))
        constants = ConstantsContext('constants', Path('core/data/constants.yaml'))
        constants.validate()

        ctx = Context('cont')
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

        ctx.adopt(const=constants)
        context.validate()
        return ctx

    def build_convertor(self, args, **kwargs):
        return JinjaConvertor(self.args.infile, self.args.outfile,
                              context=self.build_context(),
                              preamble=self.args.preamble,
                              debug=self.args.debug)

    def add_extra_arguments(self):
        self.parser.add_argument('-C', '--context', type=argparse.FileType('r'))
        self.parser.add_argument('-P', '--preamble', type=argparse.FileType('r'))


if __name__ == "__main__":
    CLIInterface().run()
