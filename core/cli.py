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

    def run(self) -> None:
        try:
            output = self.convertor.run()
            print(output, file=self.args.outfile)
            self.success()
        except Exception as e:
            self.fail()

    def fail(self):
        log.error(f"{c.err('convert: failure on ')}{c.path(self.args.infile.name)}")

    def success(self):
        if self.args.verbose:
            log.info(f"convert: {c.ok('success')} on {c.path(self.args.infile.name)}")
