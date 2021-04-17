#!/usr/bin/env python3

import argparse
import fileinput
import re
import subprocess
import sys
import tempfile

from utilities import colour as c


class Convertor():
    languages = {
        'sk':   {
            'name':     'slovak',
            'quotes':   ('„', '“'),
            'locale':   'sk-SK',
        },
        'cs':   {
            'name':     'czech',
            'quotes':   ('„', '“'),
            'locale':   'cs-CS',
        },
        'en':   {
            'name':     'english',
            'quotes':   ('“', '”'),
            'sub':      'en-US',
        },
        'ru':   {
            'name':     'russian',
            'quotes':   ('«', '»'),
            'sub':      'ruRU',
        },
        'pl':   {
            'name':     'polish',
            'quotes':   ('„', '“'),
            'sub':      'pl-PL',
        },
        'hu':   {
            'name':     'hungarian',
            'quotes':   ('„', '“'),
            'sub':      'hu-HU',
        },
        'fr':   {
            'name':     'french',
            'quotes':   ('«\u202F', '\u202F»'),
            'sub':      'fr-FR',
        },
        'qq':   {
            'name':     'test',
            'quotes':   ('(', ')'),
            'sub':      'sk-SK',
        },
    }

    postprocessing_latex = [
        (r"``", r"“"),
        (r"''", r'”'),
        (r"(?<=\\includegraphics)\[(.*)\]{(.*)}", r"[\g<1>]{\\activeDirectory/\g<2>}"),
        (r"(?<=\\includegraphics)\[(.*)\]{(.*)\.(svg|gp)}", r"[\g<1>]{\g<2>.pdf}"),
    ]

    
    def __init__(self):
        self.args = self.parse_arguments()
        self.initialize()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description             = "DeGeŠ Markdown conversion utility",
        )
        parser.add_argument('format',   choices=['latex', 'html'])
        parser.add_argument('locale',   choices=self.languages.keys())
        parser.add_argument('infile',   nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        parser.add_argument('outfile',  nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        return parser.parse_args()

    def initialize(self):
        locale = self.languages[self.args.locale]
        (self.quote_open, self.quote_close) = locale['quotes']
        self.language = locale['name']
        self.locale = locale['locale']

        self.postprocessing_latex = [(re.compile(regex), repl) for regex, repl in self.postprocessing_latex]
        self.quotes_regexes = [
            (r'"(\b)', self.quote_open + r'\g<1>'),
            (r'(\b)"', r'\g<1>' + self.quote_close),
            (r'(\S)"', r'\g<1>' + self.quote_close),
            (r'"(\S)', self.quote_open + r'\g<1>'),
        ]
        self.quotes_regexes = [(re.compile(regex), repl) for regex, repl in self.quotes_regexes]


    def run(self):
        try:
            self.file = self.file_operation(self.preprocess)(self.args.infile)
            self.file = self.call_pandoc()
            self.file = self.file_operation(self.postprocess)(self.file)
            self.write()
        except IOError as e:
            print(f"{c.path(__file__)}: Could not create a temporary file")
            fail()
        except AssertionError as e:
            print(f"{c.path(__file__)}: Calling pandoc failed")
            fail()
        else:
            print(f"{c.ok('dgs-convert: success')}")
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

    def preprocess(self, line):
        if self.filter_tags(line):
            return self.replace_quotes(self.replace_tags(line))
        else:
            return None

    def filter_tags(self, line):
        if re.match(r'^%', line) or \
            (re.match(r'^@H', line) and self.args.format == 'latex') or \
            (re.match(r'^@L', line) and self.args.format == 'html'):
            return False
        return True

    def replace_tags(self, line):
        if self.args.format == 'latex':
            line = re.sub(r'^@E\s*(.*)$', '\\\\errorMessage{\g<1>}', line)
            line = re.sub(r'^@L\s*(.*)$', '\g<1>', line)
            line = re.sub(r'^@P', '\\\\insertPicture', line)
            line = re.sub(r'^@NP', '\\\\insertPictureSimple', line)
            line = re.sub(r'^@TODO\s*(.*)$', '\\\\todoMessage{\g<1>}', line)

        if self.args.format == 'html':
            line = re.sub(r'^@H\s*(.*)$', '\g<1>', line)
            line = re.sub(r'^@P{(.*?)}{(.*?)}{(.*?)}{(.*?)}{(.*)}{(.*?)}$',
                '![\g<5>](obrazky/\g<1>.\g<3>)', line)
            line = re.sub(r'^@NP{(.*?)}{(.*?)}{(.*)}{(.*?)}$',
                '![\g<3>](obrazky/\g<1>)', line)
        return line

    def call_pandoc(self):
        out = tempfile.SpooledTemporaryFile(mode='w+')

        self.file.seek(0)
        subprocess.run([
            "pandoc",
            "--mathjax",
            "--from", "markdown+smart",
            "--pdf-engine", "xelatex",
            "--to", self.args.format,
            "--filter", "pandoc-crossref", "-M", "'crossrefYaml=core/i18n/{self.language}/crossref.yaml'",
            "--filter", "pandoc-fignos",
            "--metadata", f"lang={self.languages[self.args.locale]['locale']}",
        ], stdin=self.file, stdout=out)

        out.seek(0)
        return out

    def postprocess(self, line):
        if self.args.format == 'latex':
            for regex, replacement in self.postprocessing_latex:
                line = regex.sub(replacement, line)

        return line

    def replace_quotes(self, line):
        for regex, replacement in self.quotes_regexes:
            line = regex.sub(replacement, line)

        return line

Convertor().run()
