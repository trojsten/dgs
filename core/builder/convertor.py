import dotmap
import fileinput
import re
import subprocess
import sys
import tempfile

sys.path.append('.')

from core.utilities import colour as c


class Locale:
    def __init__(self, name, locale, quotes, **extras):
        self.name = name
        self.locale = locale
        self.quotes = quotes

        for k, v in extras.items():
            self.__setattr__(k, v)


class RegexPair:
    def __init__(self, pattern: str, repl: str, *, purpose: str):
        self._pattern = pattern
        self._repl = repl
        self.purpose = purpose

    def compile(self):
        return 


class Convertor:
    languages = {
        'sk':   Locale('slovak',    'sk-SK', ('„', '“'), figure='Obrázok', table='Tabuľka'),
        'en':   Locale('english',   'en-US', ('“', '”'), figure='Figure', table='Table'),
        'cs':   Locale('czech',     'cs-CZ', ('„', '“'), figure='Obrázek', table='Tabulka'),
        'ru':   Locale('russian',   'ru-RU', ('«', '»'), figure=''),
        'pl':   Locale('polish',    'pl-PL', ('„', '“'), figure=''),
        'hu':   Locale('hungarian', 'hu-HU', ('„', '“'), figure=''),
        'fr':   Locale('french',    'fr-FR', ('«\u202F', '\u202F»'), figure=''),
        'es':   Locale('spanish',   'es-ES', ('«', '»'), figure='Cuadro', table=''),
        'qq':   Locale('test',      'sk-SK', ('(', ')'), figure='Obrázok', table='Obrázok'),
    }

    post_regexes = {
        'latex': [
            # Change opening double quotation marks to the proper Unicode symbol
            (r"``", r"“"),
            # Change closing double quotation marks to the proper Unicode symbol
            (r"''", r'”'),
            # Change \includegraphics to protected \insertPicture (SVG and GP are converted to PDF)
            (r"\\includegraphics\[(?P<options>.*)\]{(?P<stem>.*)\.(svg|gp)}", r"\\insertPicture[\g<options>]{\g<stem>.pdf}"),
            # Change \includegraphics to protected \insertPicture (PNG, JPG and PDF are passed)
            (r"\\includegraphics\[(?P<options>.*)\]{(?P<stem>.*)\.(?P<extension>png|jpg|pdf)}", r"\\insertPicture[\g<options>]{\g<stem>.\g<extension>}"),
            # Remove empty labels and captions
            (r"^\\caption{}(\\label{.*})?\n", ""),
        ],
        'html': [
            # Prepend "obrazky/" and alter picture heights
            (
                r'<img src="(?P<filename>.*)\.(?P<extension>jpg|png|svg)"(?P<something>.*)style="height:(?P<height>[0-9.]*)mm"(?P<end>.*)>',
                r'<img src="obrazky/\g<1>.\g<2>"\g<something>style="max-width: 100%; max-height: calc(1.7 * \g<height>mm); height: calc(1.7 * \g<height>mm); margin: auto; display: block;"\g<end>>',
            ),
            (
                r'<img src="(?P<filename>.*)\.(?P<extension>gp)"(?P<something>.*)style="height:(?P<height>[0-9.]*)mm" (?P<end>.*)>',
                r'<img src="obrazky/\g<1>.png"\g<something>style="max-width: 100%; max-height: calc(1.7 * \g<height>mm); height: calc(1.7 * \g<height>mm); margin: auto; display: block;" \g<end>>',
            ),
            # Change figure title
            (
                r'<figcaption>Figure (?P<number>\d*): (?P<caption>.*)</figcaption>',
                r'<figcaption style="text-align: center;">Obrázok \g<number>: <span style="font-style: italic;">\g<caption></span></figcaption>',
            ),
            # Hack fix: incorrect display of siunitx in MathJAX (adds a one-dot to empty mantissa)
            (
                r'(\\num|\\SI){e',
                r'\g<1>{1.e',
            ),
            # Hack fix: incorrect display of siunitx in MathJAX (adds a dot after short mantissa)
            (
                r'(\\num|\\SI){([0-9])e',
                r'\g<1>{\g<2>.e',
            ),
        ],
    }

    """ DeGeŠ hacks for shorter aligned math """
    math_regexes = [
        # Beginning marker $${
        (r'^(\s*)\$\${', r'\g<1>$$\n\g<1>\\begin{aligned}'),
        # Ending marker }$$
        (r'^(\s*)}\$\$', r'\g<1>\\end{aligned}\n\g<1>$$'),
    ]

    replace_regexes = {
        'latex': [
            (r"^@E\s*(.*)$", r"\\errorMessage{\g<1>}"),
            (r"^@I\s*(.*)$", r"\\inputminted{python}{\\activeDirectory/\g<1>}"),
            (r"^@L\s*(.*)$", r"\g<1>"),
            (r"^@TODO\s*(.*)$", r"\\todoMessage{\g<1>}"),
        ],
        'html': [
            (r"^@E\s*(.*)$", r"Error: \g<1>"),
            (r"^@H\s*(.*)$", r"\g<1>"),
            (r"^@TODO\s*(.*)$", r"TODO: \g<1>"),
        ],
    }

    @staticmethod
    def compile_regexes(regexes):
        return [(re.compile(regex), repl) for (regex, repl) in regexes]

    def __init__(self, format, locale_code, infile, outfile):
        self.format = format
        self.locale_code = locale_code
        self.locale = self.languages[locale_code]
        self.infile = infile
        self.outfile = outfile

        (self.quote_open, self.quote_close) = self.locale.quotes

        quotes_regexes = [
            (r'"(_)', self.quote_close + r'\g<1>'),
            (r'"(\b)', self.quote_open + r'\g<1>'),
            (r'(\b)"', r'\g<1>' + self.quote_close),
            (r'(\S)"', r'\g<1>' + self.quote_close),
            (r'"(\S)', self.quote_open + r'\g<1>'),
        ]

        self.quotes_regexes = self.compile_regexes(quotes_regexes)
        self.math_regexes = self.compile_regexes(self.math_regexes)
        self.replace_regexes = self.compile_regexes(self.replace_regexes[self.format])
        self.post_regexes = self.compile_regexes(self.post_regexes[self.format])

    def run(self):
        try:
            #fm, tm = frontmatter.parse(self.infile.read())
            #self.infile.seek(0)
            self.file = self.file_operation(self.preprocess)(self.infile)
            self.file = self.call_pandoc()
            self.file = self.file_operation(self.postprocess)(self.file)
            self.write()
        except IOError as e:
            print(f"{c.path(__file__)}: Could not create a temporary file: {e}")
        except AssertionError as e:
            print(f"{c.path(__file__)}: Calling pandoc failed")
        except Exception as e:
            print(f"Unexpected exception occurred:")
            raise e
            return -1
        else:
            return 0

    @staticmethod
    def file_operation(function):
        """ Decorator: apply a function to every line of a file """
        def inner(f):
            out = tempfile.SpooledTemporaryFile(mode='w+')

            for line in f:
                out.write(function(line))

            out.seek(0)
            return out

        return inner

    def write(self):
        for line in self.file:
            self.outfile.write(line)
        self.file.seek(0)

    def preprocess(self, line):
        if self.filter_tags(line):
            return self.chain_process(line, [self.replace_regexes, self.quotes_regexes, self.math_regexes])
        else:
            return ""

    @staticmethod
    def process_line(line, regexes):
        for regex, replacement in regexes:
            line = regex.sub(replacement, line)
        return line

    @staticmethod
    def chain_process(line, regex_sets):
        for regex_set in regex_sets:
            line = Convertor.process_line(line, regex_set)
        return line

    def postprocess(self, line):
        return self.chain_process(line, [self.post_regexes])

    def filter_tags(self, line):
        """
        Filter by customs tags:
        -   remove lines beginning with '%'
        -   remove lines beginning with '@H' unless converting for HTML
        -   remove lines beginning with '@L' unless converting for LaTeX
        """
        if re.match(r"^%", line) or \
            (re.match(r"^@H", line) and self.format != 'html') or \
            (re.match(r"^@L", line) and self.format != 'latex'):
            return ""
        return line

    def replace_tags(self, line):
        """ Replace custom tags and pictures """
        for regex, replacement in self.replace_regexes:
            line = regex.sub(replacement, line)

        return line

    def call_pandoc(self):
        out = tempfile.SpooledTemporaryFile(mode='w+')

        self.file.seek(0)
        args = [
            "pandoc",
            "--mathjax",
            "--from", "markdown+smart",
            "--pdf-engine", "xelatex",
            "--to", self.format,
            "--filter", "pandoc-minted",
            "--filter", "pandoc-crossref", "-M", f"crossrefYaml=core/i18n/{self.locale_code}/crossref.yaml",
            "--filter", "pandoc-eqnos",
#            "--webtex='eqn://'",
            "--metadata", f"lang={self.languages[self.locale_code].locale}",
        ]
        subprocess.run(args, stdin=self.file, stdout=out)

        out.seek(0)
        return out
