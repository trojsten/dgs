#!/usr/bin/env python3

import argparse
import sys

from core.builder.convertor import Convertor
from core.utilities import colour as c


class CLIInterface():
    def __init__(self):
        self.args = self.parse_arguments()
        self.convertor = Convertor(self.args.format, self.args.locale, self.args.infile, self.args.outfile)
        result = self.convertor.run()
        if result == 0:
            self.success()
        else:
            self.fail()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description="DeGeŠ Markdown conversion utility",
        )
        parser.add_argument('format',   choices=['latex', 'html'])
        parser.add_argument('locale',   choices=Convertor.languages.keys())
        parser.add_argument('infile',   nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        parser.add_argument('outfile',  nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        parser.add_argument('--verbose', action='store_true')
        return parser.parse_args()

    def fail(self):
        print(f"{c.err('convert: failure on ')}{c.path(self.args.infile.name)}")
        sys.exit(-1)

    def success(self):
        if self.args.verbose:
            print(f"convert: {c.ok('success')} on {c.path(self.args.infile.name)}")


CLIInterface()
