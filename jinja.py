#!/usr/bin/env python
import argparse
import pprint

from pathlib import Path
from typing import Optional

import enschema
from enschema import Schema, Or

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
            'symbol': str,
            'value': Or(int, float),
            'unit': str,
            'exact': Or(int, float),
            'digits': int,
            enschema.Optional('siextra'): str,
        }
    })


class CLIInterface(cli.CLIInterface):
    description = "DeGeŠ Jinja convertor"

    def build_convertor(self, args, **kwargs):
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
        return JinjaConvertor(self.args.infile, self.args.outfile, context=ctx, debug=self.args.debug)

    def add_extra_arguments(self):
        self.parser.add_argument('-C', '--context', type=argparse.FileType('r'))


if __name__ == "__main__":
    CLIInterface()
