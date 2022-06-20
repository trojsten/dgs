#!/usr/bin/env python3

import argparse
import dotmap
import fileinput
import re
import subprocess
import sys
import tempfile

from utilities import colour as c


def compile_regexes(regexes):
    return [(re.compile(regex), repl) for (regex, repl) in regexes]


class Convertor():
    languages = {
        'sk':   {
            'name':     'slovak',
            'quotes':   ('„', '“'),
            'locale':   'sk-SK',
            'figure':   'Obrázok',
        },
        'cs':   {
            'name':     'czech',
            'quotes':   ('„', '“'),
            'locale':   'cs-CZ',
        },
        'en':   {
            'name':     'english',
            'quotes':   ('“', '”'),
            'sub':      'en-US',
        },
        'ru':   {
            'name':     'russian',
            'quotes':   ('«', '»'),
            'sub':      'ru-RU',
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
        (r"\\includegraphics\[(.*)\]{(.*)\.(svg|gp)}", r"\\insertPicture[\g<1>]{\g<2>.pdf}"),
        (r"\\includegraphics\[(.*)\]{(.*)\.(png|jpg|pdf)}", r"\\insertPicture[\g<1>]{\g<2>.\g<3>}"),
        (r"^\\caption{}(\\label{.*})?\n", ""),
    ]

    postprocessing_html = [
        (r'<img src="(.*)" style="height:(.*)" alt="(.*)">', r'<img src="\g<1>" style="max-width: 100%; max-height: calc(1.5 * \g<2>); margin: auto; display: block;" alt="\g<3>">'),
        (r'<figcaption aria-hidden="true">Figure (\d*): (.*)</figcaption>', r'<figcaption style="text-align: center;" aria-hidden="true">Obrázok \g<1>: <span style="font-style: italic;">\g<2></span></figcaption>'),
    ]

    def __init__(self):
        self.args = self.parse_arguments()
        self.initialize()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description="DeGeŠ Markdown conversion utility",
        )
        parser.add_argument('format',   choices=['latex', 'html'])
        parser.add_argument('locale',   choices=self.languages.keys())
        parser.add_argument('infile',   nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        parser.add_argument('outfile',  nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        return parser.parse_args()

    def initialize(self):
        self.locale = dotmap.DotMap(self.languages[self.args.locale], _dynamic=False)
        (self.quote_open, self.quote_close) = self.locale.quotes

        if self.args.format == 'latex':
            self.postprocessing = [(re.compile(regex), repl) for regex, repl in self.postprocessing_latex]
        if self.args.format == 'html':
            self.postprocessing = [(re.compile(regex), repl) for regex, repl in self.postprocessing_html]

        self.quotes_regexes = compile_regexes([
            (r'"(\b)', self.quote_open + r'\g<1>'),
            (r'(\b)"', r'\g<1>' + self.quote_close),
            (r'(\S)"', r'\g<1>' + self.quote_close),
            (r'"(\S)', self.quote_open + r'\g<1>'),
        ])

        self.math_regexes = compile_regexes([
            (r'^\$\${$', r'$$\n\\begin{aligned}'),
            (r'^}\$\$', r'\\end{aligned}\n$$'),
        ])

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
        except Exception as e:
            print(f"Unexpected exception occurred:")
            raise e
            self.fail()
        else:
            self.finish()


    def fail(self):
        print(f"pandoc-convert: {c.err('failure')} on {c.path(self.args.infile.name)}")
        sys.exit(-1)

    def finish(self):
        print(f"pandoc-convert: {c.ok('success')} on {c.path(self.args.infile.name)}")
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
            print(self.replace_math(self.replace_quotes(self.replace_tags(line))), end='')
            return self.replace_math(self.replace_quotes(self.replace_tags(line)))
        else:
            return None

    def filter_tags(self, line):
        if re.match(r"^%", line) or \
            (re.match(r"^@H", line) and self.args.format == 'latex') or \
            (re.match(r"^@L", line) and self.args.format == 'html'):
            return False
        return True

    def replace_tags(self, line):
        if self.args.format == 'latex':
            line = re.sub(r"^@E\s*(.*)$", r"\\errorMessage{\g<1>}", line)
            line = re.sub(r"^@L\s*(.*)$", r"\g<1>", line)
            line = re.sub(r"^@TODO\s*(.*)$", r"\\todoMessage{\g<1>}", line)

        if self.args.format == 'html':
            line = re.sub(r"^@E\s*(.*)$", r"Error: \g<1>", line)
            line = re.sub(r"^@H\s*(.*)$", "\g<1>", line)
            line = re.sub(
                r"^!\[(?P<caption>.*)\]\((?P<filename>.*)\.(?P<extension>jpg|png)\){(?P<extras>.*)}$",
                r"![\g<caption>](obrazky/\g<filename>.\g<extension>){\g<extras>}",
                line
            )
            line = re.sub(
                r"^!\[(?P<caption>.*)\]\((?P<filename>.*)\.(?P<extension>gp|svg)\){(?P<extras>.*)}$",
                r"![\g<caption>](obrazky/\g<filename>.png){\g<extras>}",
                line
            )
            line = re.sub(
                r"^!\[(?P<caption>.*)\]\(obrazky/(?P<filename>.*)\.(?P<extension>.*)\){height(?P<extras>.*)}$",
                r"![\g<caption>](obrazky/\g<filename>.\g<extension>){#fig:\g<filename> height\g<extras>}",
                line
            )
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
#            "--filter", "pandoc-fignos", "-M", f'fignos-caption-name="{self.locale.figure}"',
            "--filter", "pandoc-eqnos",
            "--metadata", f"lang={self.languages[self.args.locale]['locale']}",
        ], stdin=self.file, stdout=out)

        out.seek(0)
        return out

    def postprocess(self, line):
        for regex, replacement in self.postprocessing:
            line = regex.sub(replacement, line)
        return line

    def replace_quotes(self, line):
        for regex, replacement in self.quotes_regexes:
            line = regex.sub(replacement, line)

        return line

    def replace_math(self, line):
        for regex, replacement in self.math_regexes:
            line = regex.sub(replacement, line)

        return line

Convertor().run()
