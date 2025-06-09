#!/usr/bin/env python

import argparse
import logging
import sys

from abc import abstractmethod

from core import i18n
from core.utilities import colour as c

log = logging.getLogger('dgs')


class CLIInterface:
    description: str = "<empty>"

    def __init__(self):
        self.parser = argparse.ArgumentParser(description=self.description)
        self.add_default_arguments()
        self.add_extra_arguments()
        self.args = self.parser.parse_args()

        if self.args.debug:
            log.setLevel(logging.DEBUG)

        self.convertor = self.build_convertor(self.args)

        if self.convertor.run() == 0:
            self.success()
        else:
            self.fail()

    @abstractmethod
    def build_convertor(self, args, **kwargs):
        pass

    def add_default_arguments(self):
        self.parser.add_argument('locale',   choices=i18n.languages.keys())
        self.parser.add_argument('infile',   nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        self.parser.add_argument('outfile',  nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        self.parser.add_argument('-v', '--verbose', action='store_true')
        self.parser.add_argument('-d', '--debug', action='store_true')

    @staticmethod
    def add_extra_arguments():
        pass

    def fail(self):
        print(f"{c.err('convert: failure on ')}{c.path(self.args.infile.name)}")
        sys.exit(-1)

    def success(self):
        if self.args.verbose:
            print(f"convert: {c.ok('success')} on {c.path(self.args.infile.name)}")
