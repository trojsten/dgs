#!/usr/bin/env python
import argparse

from pathlib import Path
from typing import Any, Optional

from core import cli
from core.builder.context import Context
from core.builder.jinja import JinjaRenderer


class JinjaConvertor:
    def __init__(self, infile: Path, outfile: Optional[Path], context: dict[str, Any]):
        self.renderer = JinjaRenderer(Path(infile.name).parent)
        self.infile: Path = Path(infile.name).name
        self.outfile: Optional[Path] = outfile
        self.context: Context = None

        self.context = Context('default', **{'a': 3, 'b': 5, 'c': 7})

    def run(self):
        self.renderer.render(self.infile, self.context.data, outfile=self.outfile)
        return 0



class CLIInterface(cli.CLIInterface):
    description = "DeGeŠ Jinja convertor"

    def build_convertor(self, args, **kwargs):
        return JinjaConvertor(self.args.infile, self.args.outfile, {'a': 'c'})

    def add_extra_arguments(self):
        self.parser.add_argument('context', type=argparse.FileType('w'))


if __name__ == "__main__":
    CLIInterface()
