#!/usr/bin/env python

from core import cli
from core.builder.convertor import Convertor


class CLIInterface(cli.CLIInterface):
    description = "DeGeŠ Markdown convertor"

    def build_convertor(self, args, **kwargs):
        return Convertor(args.format, args.locale, args.infile, args.outfile, math=args.math)

    def add_extra_arguments(self):
        self.parser.add_argument('--format', type=str, choices=['latex', 'html'])
        self.parser.add_argument('--math',   type=str, choices=['webtex', 'mathjax'], default='mathjax')


if __name__ == "__main__":
    CLIInterface().run()
