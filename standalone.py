#!/usr/bin/env python

from core import cli
from core.builder.standalone import BuilderStandalone


class CLIInterface(cli.CLIInterface):
    def build_convertor(self, args, **kwargs):
        return BuilderStandalone(args.locale, self.infile, self.outfile)


if __name__ == "__main__":
    CLIInterface()
