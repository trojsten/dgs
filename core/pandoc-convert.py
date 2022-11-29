#!/usr/bin/env python3

import argparse
import dotmap
import fileinput
import re
import subprocess
import sys
import tempfile
import frontmatter

from utilities import colour as c


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
            'locale':   'en-US',
        },
        'ru':   {
            'name':     'russian',
            'quotes':   ('«', '»'),
            'locale':   'ru-RU',
        },
        'pl':   {
            'name':     'polish',
            'quotes':   ('„', '“'),
            'locale':   'pl-PL',
        },
        'hu':   {
            'name':     'hungarian',
            'quotes':   ('„', '“'),
            'locale':   'hu-HU',
        },
        'fr':   {
            'name':     'french',
            'quotes':   ('«\u202F', '\u202F»'),
            'locale':   'fr-FR',
        },
        'es':   {
            'name':     'spanish',
            'quotes':   ('«', '»'),
            'locale':   'es-ES',
        },
        'qq':   {
            'name':     'test',
            'quotes':   ('(', ')'),
            'locale':   'sk-SK',
        },
    }

    postprocessing = {
        'latex': [
            (r"``", r"“"),
            (r"''", r'”'),
            (r"\\includegraphics\[(.*)\]{(.*)\.(svg|gp)}", r"\\insertPicture[\g<1>]{\g<2>.pdf}"),
            (r"\\includegraphics\[(.*)\]{(.*)\.(png|jpg|pdf)}", r"\\insertPicture[\g<1>]{\g<2>.\g<3>}"),
            (r"^\\caption{}(\\label{.*})?\n", ""),
        ],
        'html': [
            (
                r'<img src="(.*)" (.*)id="(.*)" style="height:([0-9.]*)mm" (.*)>',
                r'<img src="\g<1>" \g<2>id="\g<3>" style="max-width: 100%; max-height: calc(1.7 * \g<4>mm); margin: auto; display: block;" \g<5>>',
            ),
            (
                r'<figcaption aria-hidden="true">Figure (\d*): (.*)</figcaption>',
                r'<figcaption style="text-align: center;" aria-hidden="true">Obrázok \g<1>: <span style="font-style: italic;">\g<2></span></figcaption>',
            ),
        ],
    }


    math_regexes = [
        (r'^(\s*)\$\${$', r'\g<1>$$\n\\begin{aligned}'),
        (r'^(\s*)}\$\$', r'\g<1>\\end{aligned}\n$$'),
    ]
    replace_regexes = {
        'latex': [
            (r"^@E\s*(.*)$", r"\\errorMessage{\g<1>}"),
            (r"^@L\s*(.*)$", r"\g<1>"),
            (r"^@TODO\s*(.*)$", r"\\todoMessage{\g<1>}"),
        ],
        'html': [
            (r"^@E\s*(.*)$", r"Error: \g<1>"),
            (r"^@H\s*(.*)$", "\g<1>"),
            (
                r"^!\[(?P<caption>.*)\]\((?P<filename>.*)\.(?P<extension>jpg|png|svg)\){(?P<extras>.*)}$",
                r"![\g<caption>](obrazky/\g<filename>.\g<extension>){\g<extras>}",
            ),
            (
                r"^!\[(?P<caption>.*)\]\((?P<filename>.*)\.(?P<extension>gp)\){(?P<extras>.*)}$",
                r"![\g<caption>](obrazky/\g<filename>.png){\g<extras>}",
            ),
            (
                r"^!\[(?P<caption>.*)\]\(obrazky/(?P<filename>.*)\.(?P<extension>.*)\){height(?P<extras>.*)}$",
                r"![\g<caption>](obrazky/\g<filename>.\g<extension>){#fig:\g<filename> height\g<extras>}",
            ),
        ],
    }

    @staticmethod
    def compile_regexes(regexes):
        return [(re.compile(regex), repl) for (regex, repl) in regexes]

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

        quotes_regexes = [
            (r'"(_)', self.quote_close + r'\g<1>'),
            (r'"(\b)', self.quote_open + r'\g<1>'),
            (r'(\b)"', r'\g<1>' + self.quote_close),
            (r'(\S)"', r'\g<1>' + self.quote_close),
            (r'"(\S)', self.quote_open + r'\g<1>'),
        ]

        self.postprocessing = self.compile_regexes(self.postprocessing[self.args.format])
        self.quotes_regexes = self.compile_regexes(quotes_regexes)
        self.math_regexes = self.compile_regexes(self.math_regexes)
        self.replace_regexes = self.compile_regexes(self.replace_regexes[self.args.format])

    def run(self):
        try:
            fm, tm = frontmatter.parse(self.args.infile.read())
            self.args.infile.seek(0)
            self.file = self.file_operation(self.preprocess)(self.args.infile)
            self.file = self.call_pandoc()
            self.file = self.file_operation(self.postprocess)(self.file)
            self.write()
        except IOError as e:
            print(f"{c.path(__file__)}: Could not create a temporary file")
            self.fail()
        except AssertionError as e:
            print(f"{c.path(__file__)}: Calling pandoc failed")
            self.fail()
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
            return self.replace_math(self.replace_quotes(self.replace_tags(line)))
        else:
            return None

    def filter_tags(self, line):
        """
            Filter by customs tags:
            -   remove lines beginning with '%'
            -   remove lines beginning with '@H' if not converting for HTML
            -   remove lines beginning with '@L' if not converting for LaTeX
        """
        if re.match(r"^%", line) or \
            (re.match(r"^@H", line) and self.args.format != 'html') or \
            (re.match(r"^@L", line) and self.args.format != 'latex'):
            return False
        return True

    def replace_tags(self, line):
        """
            Replace custom tags and pictures
        """
        for regex, replacement in self.replace_regexes:
            line = regex.sub(replacement, line)

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
