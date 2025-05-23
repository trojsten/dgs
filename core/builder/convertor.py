import subprocess
import tempfile
from tempfile import SpooledTemporaryFile
from typing import Callable, TextIO
from pathlib import Path

from core.utilities import colour as c
from .classes import RegexFailure, RegexReplacement
from core import i18n


class Convertor:
    post_regexes = {
        'all': [],
        'latex': [
            # Change \includegraphics to protected \insertPicture (SVG and GP are converted to PDF)
            RegexReplacement(r"\\includegraphics(?P<options>\[.*\])?{(?P<stem>.*)\.(svg|gp|tikz)}",
                             r"\\insertPicture\g<options>{\g<stem>.pdf}",
                             purpose=r"Change \includegraphics to protected \insertPicture"),
            # Change \includesvg to protected \insertPicture (SVG and GP are converted to PDF)
            RegexReplacement(r"\\includesvg\[(?P<options>.*)\]{(?P<stem>.*)\.(svg|gp)}",
                             r"\\begin{figure}\\centering\\insertPicture[\g<options>]{\g<stem>.pdf}\\end{figure}",
                             purpose=r"Change \includesvg to protected \insertPicture"),
            # Change \includegraphics to protected \insertPicture (PNG, JPG and PDF are passed)
            RegexReplacement(r"\\includegraphics\[(?P<options>.*)\]{(?P<stem>.*)\.(?P<extension>png|jpg|pdf)}",
                             r"\\insertPicture[\g<options>]{\g<stem>.\g<extension>}",
                             purpose=r"Change \includegraphics to protected \insertPicture"),
            # Remove empty labels and captions
            RegexReplacement(r"^\\caption{}(\\label{.*})?\n", "", purpose="Remove empty captions and labels"),
        ],
        'html': [
            # Prepend "obrazky/"
            RegexReplacement(
                r'<img src="(?P<filename>.*)\.(?P<extension>jpg|png|svg)"',
                r'<img src="obrazky/\g<filename>.\g<extension>"',
            ),
            RegexReplacement(
                r'<img src="(?P<filename>.*)\.gp"',
                r'<img src="obrazky/\g<filename>.png"',
            ),
            # alter picture heights
            RegexReplacement(
                r'style="height:(?P<height>[0-9.]*)mm"',
                r'style="max-width: 100%; max-height: calc(1.7 * \g<height>mm); margin: auto; display: block;"',
            ),
            # Change figure title
            RegexReplacement(
                r'<figcaption>Obrázok (?P<number>\d*):',
                r'<figcaption style="text-align: center;">Obrázok \g<number>: <span style="font-style: italic;">',
            ),
            # Hack fix: incorrect display of siunitx in MathJAX (adds a one-dot to empty mantissa)
            RegexReplacement(
                r'(\\num|\\SI){e',
                r'\g<1>{1.e',
            ),
            # Hack fix: incorrect display of siunitx in MathJAX (adds a dot after short mantissa)
            RegexReplacement(
                r'(\\num|\\SI){([0-9])e',
                r'\g<1>{\g<2>.e',
            ),
        ],
    }

    post_checks = {
        'all': [],
        'html': [
            # This is just a temporary workaround for Trojstenweb's inane choice of paths
            RegexFailure(r'<img src="(?!obrazky)', error="Caught an image without 'obrazky/'"),
            RegexFailure(r'\\includegraphics', error=r"Caught an unconverted \\includegraphics"),
            RegexFailure(r'\\includesvg', error=r"Caught an unconverted \\includesvg"),
            RegexFailure(r'@L', error="LaTeX-only tag in HTML"),
        ],
        'latex': [
            RegexFailure(r'@H', error="HTML-only tag in LaTeX"),
        ],
    }

    pre_regexes = {
        'all': [
            RegexReplacement(r'^%.*$', r'', purpose="Comment"),
            RegexReplacement(r'(^|(\s*))\$\${', r'\g<1>$$\n\g<1>\\begin{aligned}', purpose="Beginning align marker"),
            RegexReplacement(r'(^|(\s+))}\$\$', r'\g<1>\\end{aligned}\n\g<1>$$', purpose="Ending align marker"),
        ],
        'latex': [
            RegexReplacement(r"^@E\s*(.*)$", r"\\errorMessage{\g<1>}", purpose="Replace error tag"),
            RegexReplacement(r"^@L\s*(.*)$", r"\g<1>", purpose="Keep LaTeX-only lines"),
            RegexReplacement(r"^@H\s*(.*)$", r"", purpose="Remove HTML-only tag"),
            RegexReplacement(r"^@T([Oo][Dd][Oo])?\s*(.*)$", r"\\todoMessage{\g<2>}", purpose="Replace TODO tag"),
        ],
        'html': [
            RegexReplacement(r"^@E\s*(.*)$", r"Error: \g<1>", purpose="Replace error tag"),
            RegexReplacement(r"^@L\s*(.*)$", r"", purpose="Remove LaTeX-only lines"),
            RegexReplacement(r"^@H\s*(.*)$", r"\g<1>", purpose="Keep HTML-only tag"),
            RegexReplacement(r"^@T([Oo][Dd][Oo])?\s*(.*)$", r"TODO: \g<2>", purpose="Replace TODO tag"),
            RegexReplacement(r"\\qty", r"\\SI", purpose="Revert to old siunitx syntax for old failing web"),
            RegexReplacement(r"\\unit", r"\\si", purpose="Revert to old siunitx syntax for old failing web"),
        ],
    }

    pre_checks = {
        'all': [
            RegexFailure(r'(<<<<<<<<|========|>>>>>>>>)', error="Git conflict markers present"),
            RegexFailure(r'\^\\circ|\^{\\circ}', error=r"No \circ allowed in exponents"),
        ],
        'latex': [],
        'html': [],
    }

    def __init__(self, output_format: str, locale_code: str, infile, outfile, **options):
        self.output_format: str = output_format
        self.locale_code: str = locale_code
        self.locale: i18n.Locale = i18n.languages[locale_code]
        self.infile = infile
        self.outfile = outfile
        self.math = options.get('math', 'mathjax')
        self.file = None

        assert output_format in ['html', 'latex'], "Output format is neither 'html' nor 'latex'!"

        # regexes = yaml.safe_load(open('core/builder/regexes.yaml', 'rb'))

        (self.quote_open, self.quote_close) = self.locale.quotes

        self.quotes_regexes = [
            RegexReplacement(r'"(_)', self.quote_close + r'\g<1>'),
            RegexReplacement(r'"(\b)', self.quote_open + r'\g<1>'),
            RegexReplacement(r'(\b)"', r'\g<1>' + self.quote_close),
            RegexReplacement(r'(\S)"', r'\g<1>' + self.quote_close),
            RegexReplacement(r'"(\S)', self.quote_open + r'\g<1>'),
        ]

        self.pre_regexes['all'] += [
            # Currently nothing
        ]

        self.pre_checks = self._filter_regexes(self.pre_checks)
        self.pre_regexes = self._filter_regexes(self.pre_regexes)
        self.post_checks = self._filter_regexes(self.post_checks)
        self.post_regexes = self._filter_regexes(self.post_regexes)

    def _filter_regexes(self, regex_set: dict[str, list]) -> list:
        return regex_set['all'] + regex_set[self.output_format]

    def run(self):
        try:
            self.file = self.file_operation(self.pre_check)(self.infile)
            self.file = self.file_operation(self.preprocess)(self.file)
            self.file = self.call_pandoc()
            self.file = self.file_operation(self.postprocess)(self.file)
            self.file = self.file_operation(self.post_check)(self.file)
            self.write()
        except IOError as e:
            print(f"{c.path(__file__)}: Could not create a temporary file: {e}")
        except AssertionError as e:
            print(f"{c.path(__file__)}: Calling pandoc failed: {e}")
        except Exception as e:
            print("Unexpected exception occurred:")
            raise e
        else:
            return 0

    @staticmethod
    def file_operation(function: Callable) -> Callable:
        """Decorator: apply a function to every line of a file"""
        def inner(f: SpooledTemporaryFile[str]) -> SpooledTemporaryFile[str]:
            out = SpooledTemporaryFile(mode='w+')
            for line in f:
                out.write(function(line))
            out.seek(0)
            return out

        return inner

    def write(self):
        for line in self.file:
            self.outfile.write(line)
        self.file.seek(0)

    @staticmethod
    def process_line(line: str, regexes) -> str:
        for regex in regexes:
            line = regex.pattern.sub(regex.repl, line)
        return line

    @staticmethod
    def check_line(line: str, regexes) -> str:
        for regex in regexes:
            if regex.pattern.search(line):
                raise Exception(regex.error)
        return line

    @staticmethod
    def chain_process(line: str, regex_sets: list, *, func=process_line) -> str:
        for regex_set in regex_sets:
            line = func(line, regex_set)
        return line

    def preprocess(self, line):
        # return self.chain_process(line, [self.pre_regexes, self.quotes_regexes]) # Turned off for quote testing!
        return self.chain_process(line, [self.pre_regexes])

    def postprocess(self, line):
        return self.chain_process(line, [self.post_regexes])

    def pre_check(self, line):
        return self.chain_process(line, [self.pre_checks], func=self.check_line)

    def post_check(self, line):
        return self.chain_process(line, [self.post_checks], func=self.check_line)

    def call_pandoc(self):
        out = tempfile.SpooledTemporaryFile(mode='w+')

        self.file.seek(0)
        args = [
            "pandoc",
            "--metadata", f"lang={self.locale.id}",
            "-V", "csquotes=true",
            "--from", "markdown+smart",
            "--pdf-engine", "xelatex",
            "--to", self.output_format,
            "--filter", "pandoc-crossref",
            "-M", f"crossrefYaml=build/core/i18n/{self.locale_code}.yaml",
            "--filter", "pandoc-include",
            "-M", f"include-entry={Path(self.infile.name).parent}/",
            "-M", f"rewrite-path=false",
            "--filter", "pandoc-minted",
            "--lua-filter", "./core/filters/quotes.lua",
        ]
        if self.output_format == 'html':
            args += [
                "--webtex='eqn://'" if self.math == 'webtex' else "--mathjax",
            ]

        subprocess.run(args, stdin=self.file, stdout=out)

        out.seek(0)
        return out
