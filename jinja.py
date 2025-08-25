#!/usr/bin/env python
import argparse
import numbers
import pprint
from abc import ABC

from pathlib import Path
from typing import Optional

from enschema import Schema, Or, Optional as Opt

from core import cli
from core.builder.context.context import Context
from core.builder.context.file import FileContext
from core.builder.jinja import MarkdownJinjaRenderer

from core.builder.context.constant import PhysicsConstant


VALID_TAGS: dict[str, str] = {
    'kinematics': 'kinematics',
    'statics': 'statics',
    'electrostatics': 'electrostatics',
    'uam': 'uniformly accelerated motion',
    'thermodynamics': 'thermodynamics',
    'buoyancy': 'buoyancy',
    'troll': 'a problem with a trivial solution',
    'elegant': 'short but interesting problem',
}


def valid_tag(tag: str) -> bool:
    return tag in VALID_TAGS


class JinjaConvertor:
    def __init__(self,
                 infile: Path,
                 outfile: Optional[Path],
                 *,
                 context: Context,
                 debug: bool = False):
        self.renderer = MarkdownJinjaRenderer(Path(infile.name).parent)
        self.infile: Path = Path(infile.name)
        self.outfile: Optional[Path] = outfile
        self.context: Context = context

        if debug:
            pprint.pprint(context.data)

    def run(self):
        self.renderer.render(self.infile.name, self.context.data, outfile=self.outfile)
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
        'tags': list[valid_tag],
        Opt('values'): dict[str, PhysicsConstant],
    })


class CLIInterface(cli.CLIInterface, ABC):
    """
    Abstract base class for DGS CLI interfaces
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
        return JinjaConvertor(self.args.infile, self.args.outfile, context=self.build_context(), debug=self.args.debug)

    def add_extra_arguments(self):
        self.parser.add_argument('-C', '--context', type=argparse.FileType('r'))


if __name__ == "__main__":
    CLIInterface().run()
