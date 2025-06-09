#!/usr/bin/env python
import argparse
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
        str: {
            'symbol': str,                              # TeX-formatted unit
            'value': Or(int, float),
            'unit': str,                                # `siunitx`-formatted unit
            'digits': int,                              # Digits to be used in approximations
            Opt('siextra'): str,                        # Extra `siunitx` data to be included as \qty[siextra]{...}{...}
            Opt('force_f', default=False): bool,        # Force '.f' format specifier
        }
    })


class CLIInterface(cli.CLIInterface, ABC):
    """
    Abstract base class for DGS CLI interfaces
    """
    description = "DeGeŠ Jinja convertor"

    def build_context(self) -> Context:
        context = FileContext('context', Path(self.args.context.name))
        constants = ConstantsContext('constants', Path('core/data/constants.yaml'))

        ctx = Context('cont')
        if 'values' in context.data:
            values = context.data['values']

            for key, value in values.items():
                if isinstance(value, dict):
                    values[key] = PhysicsConstant(key, **value)

            ctx.add(**values)
        ctx.add(const={
            name: PhysicsConstant(name, **data) for name, data in constants.data.items()
        })

        return ctx

    def build_convertor(self, args, **kwargs):
        return JinjaConvertor(self.args.infile, self.args.outfile, context=self.build_context(), debug=self.args.debug)

    def add_extra_arguments(self):
        self.parser.add_argument('-C', '--context', type=argparse.FileType('r'))


if __name__ == "__main__":
    CLIInterface()
