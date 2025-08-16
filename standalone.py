#!/usr/bin/env python

from core import cli
from core.builder.standalone import StandaloneRenderer


class CLIInterface(cli.CLIInterface):
    def build_convertor(self, args, **kwargs):
        return StandaloneRenderer(args.locale, args.infile, args.outfile)


if __name__ == "__main__":
    CLIInterface()
