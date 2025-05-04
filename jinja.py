#!/usr/bin/env python
import argparse
import pprint

from pathlib import Path
from typing import Optional

from core import cli
from core.builder.context.context import Context
from core.builder.context.file import FileContext
from core.builder.jinja import JinjaRenderer, MarkdownRenderer

from core.builder.context.constant import PhysicsConstant


class JinjaConvertor:
    def __init__(self,
                 infile: Path,
                 outfile: Optional[Path],
                 *,
                 context: Context):
        self.renderer = MarkdownRenderer(Path(infile.name).parent)
        self.infile: Path = Path(infile.name).name
        self.outfile: Optional[Path] = outfile
        self.context: Context = context

        #pprint.pprint(context.data)

    def run(self):
        self.renderer.render(self.infile, self.context.data, outfile=self.outfile)
        return 0


class CLIInterface(cli.CLIInterface):
    description = "DeGeŠ Jinja convertor"

    def build_convertor(self, args, **kwargs):
        context = FileContext('context', Path(self.args.context.name))
        constants = FileContext('constants', Path('/home/kvik/dgs/source/naboj/phys/meta.yaml'))
        ctx = Context('cont')
        if 'values' in context.data:
            ctx.add(**context.data['values'])

        ctx.add(const={
            name: PhysicsConstant(name, **data) for name, data in constants.data['constants'].items()
        })
        return JinjaConvertor(self.args.infile, self.args.outfile, context=ctx)

    def add_extra_arguments(self):
        self.parser.add_argument('context', type=argparse.FileType('r'))


if __name__ == "__main__":
    CLIInterface()
