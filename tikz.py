#!/usr/bin/env python

import argparse
import sys

from core import i18n
from core.builder.tikz import TikzRenderer
from core.utilities import colour as c


class CLIInterface:
    def __init__(self):
        self.args = self.parse_arguments()
        self.convertor = TikzRenderer(self.args.locale, self.args.infile, self.args.outfile)
        if self.convertor.run() == 0:
            self.success()
        else:
            self.fail()

    @staticmethod
    def parse_arguments():
        parser = argparse.ArgumentParser(
            description="DeGeŠ Markdown conversion utility",
        )
        parser.add_argument('locale',   choices=i18n.languages.keys())
        parser.add_argument('infile',   nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        parser.add_argument('outfile',  nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        parser.add_argument('--verbose', action='store_true')
        return parser.parse_args()

    def fail(self):
        print(f"{c.err('tikz: failure on ')}{c.path(self.args.infile.name)}")
        sys.exit(-1)

    def success(self):
        if self.args.verbose:
            print(f"tikz: {c.ok('success')} on {c.path(self.args.infile.name)}")


if __name__ == "__main__":
    CLIInterface()
