#!/usr/bin/env python3

import argparse
import fileinput
import re
import subprocess
import sys
import tempfile

from utilities import colour as c


class Convertor():
    def __init__(self):
        self.args = self.parse_arguments()
        self.initialize()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description             = "DeGeŠ Markdown conversion utility",
        )
        parser.add_argument('infile',   nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        parser.add_argument('outfile',  nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        return parser.parse_args()

    def initialize(self):
        pass


    def run(self):
        self.regex = re.compile(r'^@P{(.*?)}{(.*?)}{(.*?)}{(.*?)}{(.*)}{(.*?)}$')
        self.regex = re.compile(r'^@NP{(.*?)\.(.*?)}{(.*?)}{(.*)}{(.*?)}$')
        try:
            self.file = self.file_operation(self.processNP)(self.args.infile)
            self.write()
        except IOError as e:
            print(f"{c.path(__file__)}: Could not create a temporary file")
            self.fail()
        except AssertionError as e:
            print(f"{c.path(__file__)}: Calling pandoc failed")
            self.fail()
        except Exception as e:
            self.fail()
        else:
            self.finish()

    def fail(self):
        print(f"picture-convert: {c.err('failure')} on {c.path(self.args.infile.name)}")
        sys.exit(-1)

    def finish(self):
        print(f"picture-convert: {c.ok('success')} on {c.path(self.args.infile.name)}")
        sys.exit(0)

    def file_operation(self, function):
        def inner(f):
            out = tempfile.SpooledTemporaryFile(mode = 'w+')

            for line in f:
                line = function(line)
                if line is not None:
                    out.write(line)

            out.seek(0)
            return out

        return inner

    def write(self):
        for line in self.file:
            self.args.outfile.write(line)

        self.file.seek(0)

    def processP(self, line):
        if found := self.regex.findall(line):
            m = found[0]
            caption = m[4]
            name = m[0]

            if m[1] == m[2]:
                ext = m[1]
            else:
                if m[1] == 'pdf' and m[2] == 'png':
                    ext = 'svg'
                else:
                    ext = m[1]

            height = m[3]
            label = "" if m[5] == '' else f"#{m[5]} "
            return f"![{caption}]({name}.{ext}){{{label}height={height}}}\n"
        return line

    def processNP(self, line):
        if found := self.regex.findall(line):
            m = found[0]

            name = m[0]
            ext = m[1]
            height = m[2]
            caption = m[3]

            if ext == 'pdf':
                ext = 'svg'

            label = "" if m[4] == '' else f"#{m[4]} "
            return f"![{caption}]({name}.{ext}){{{label}height={height}}}\n"
        return line


Convertor().run()
