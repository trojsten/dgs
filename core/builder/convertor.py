import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from tempfile import SpooledTemporaryFile

from core import i18n
from core.filters import dgsmacros, siunitx

from .classes import RegexFailure, RegexReplacement


class Convertor:
    post_regexes = {
        'all': [],
        'latex': [
            # Change \includegraphics to protected \insertPicture (SVG and GP are converted to PDF)
            RegexReplacement(r"\\includegraphics(?P<options>\[.*\])?{(?P<stem>.*)\.(svg|gp|tikz)}",
                             r"\\insertPicture\g<options>{\g<stem>.pdf}",
                             purpose=r"Change \includegraphics to protected \insertPicture"),
            # An empty path is a picture nobody has drawn yet. `\insertPicture` already draws
            # `example-image` -- a grey panel with a cross through it -- for a file that is not
            # there, so `![](){height=40mm}` is all a placeholder needs to be, and it renders as
            # something plainly missing rather than as nothing at all. Without this rule it does
            # not reach `\insertPicture` at all: the rules around it match on the extension, so
            # a path with none stays a bare `\includegraphics{}` and stops xelatex with
            # ``File `\' not found``. Matching only the *empty* path and not every extensionless
            # one keeps a mistyped `![](figure)` loud, which it should be.
            RegexReplacement(r"\\includegraphics(?P<options>\[.*\])?{}",
                             r"\\insertPicture\g<options>{}",
                             purpose=r"An empty picture path still goes through \insertPicture"),
            # Change \includesvg to protected \insertPicture (SVG and GP are converted to PDF).
            # No \begin{figure} wrapper here: pandoc already emits one around captioned images, so
            # adding another produced a float nested inside a float. \insertPicture centres on its
            # own, so uncaptioned pictures need no wrapper either -- this is exactly how the
            # \includegraphics rules above and below behave.
            RegexReplacement(r"\\includesvg(?P<options>\[.*\])?{(?P<stem>.*)\.(svg|gp)}",
                             r"\\insertPicture\g<options>{\g<stem>.pdf}",
                             purpose=r"Change \includesvg to protected \insertPicture"),
            # Change \includegraphics to protected \insertPicture (PNG, JPG and PDF are passed through unchanged)
            RegexReplacement(r"\\includegraphics(?P<options>\[.*\])?{(?P<stem>.*)\.(?P<extension>png|jpg|pdf)}",
                             r"\\insertPicture\g<options>{\g<stem>.\g<extension>}",
                             purpose=r"Change \includegraphics to protected \insertPicture"),
            # An empty caption used to be deleted here, and its `\label` with it. That is the
            # one thing it must not do now: **a caption is what makes pandoc emit a `figure`**,
            # and so what gives a drawing its number and its label, which is why
            # `figure_captions` gives every solution figure one whether the author wrote text or
            # not. Stripping it put the figure straight back to where it started -- unnumbered,
            # and with a `\label` that no `[-@fig:…]` could reach, which is the defect
            # `18/firework-bee/en` prints as `??`.
            #
            # Removing the rule is inert for everything that exists: no source writes an empty
            # alt text and no file under `build/` carried a `\caption{}` before this.
        ],
        'html': [
            # A picture becomes an SVG, mirroring what the LaTeX rules above do with `.pdf`.
            # One target extension for every source, because `build/%.svg` takes a picture from
            # any of them; a raster picture is already web-ready and is left alone.
            #
            # These also stopped prepending `obrazky/`, a directory the build has never produced,
            # which had made every image in every fragment a broken link -- in seminar too, which
            # is what the web actually ships.
            RegexReplacement(r'<img src="(?P<stem>[^"]*)\.tikz"', r'<img src="\g<stem>.svg"',
                             purpose="A TikZ picture is an SVG on the web"),
            RegexReplacement(r'<img src="(?P<stem>[^"]*)\.gp"', r'<img src="\g<stem>.svg"',
                             purpose="A gnuplot picture is an SVG on the web"),
            RegexReplacement(r'<img src="(?P<stem>[^"]*)\.pdf"', r'<img src="\g<stem>.svg"',
                             purpose="A PDF picture is an SVG on the web"),
            # `|arr` separates its rows with `\\\\[\\jot]`, because `array` zeroes the lengths
            # `\\openup` raises and two rows of display-style fractions would otherwise touch.
            # `\\jot` is a TeX length register and MathJax has no notion of one, so it reads the
            # bracket as a dimension it cannot parse and refuses the whole block with
            # `Bracket argument to \\\\ must be a dimension` -- in red, in place of the equations.
            # Every one of the 125 `|arr` call sites in `source/` was unrenderable on the web.
            #
            # `dgs.cls` puts `\\jot` at 10pt; the web gets that as an explicit length, which is the
            # one thing MathJax will take. Still needed after the maths was moved to build time:
            # `page.py --maths mathjax` is one of the two engines, not a fallback.
            RegexReplacement(
                r'\\\\\[\\jot\]',
                r'\\\\[10pt]',
                purpose=r'MathJax cannot read `\jot` as a dimension',
            ),
            # Mark the caption's label off from its text, so the stylesheet can set the number
            # upright and the text italic, as the booklet does. The styling itself is
            # `figcaption` in `core/html/page.css`; this rule only supplies the spans it needs.
            #
            # **It keys on the number, not on the word**, because the word is the locale's:
            # pandoc-crossref takes it from `figureTitle` in `build/core/i18n/<lang>.yaml`, so it
            # is `Obrázok`, `Figure`, `Abbildung`, `Ábra` and seven more. This rule used to match
            # `<figcaption>Obrázok (\d*):` -- Slovak, hardcoded -- so ten of the eleven languages
            # could never have matched it.
            #
            # They were not missing anything, which is the part worth keeping in mind: the rule
            # had stopped firing for **every** language, Slovak included, because pandoc writes
            # `<figcaption aria-hidden="true">` and the pattern wanted a bare `<figcaption>`.
            # 209 built fragments carry a caption and not one of them was styled. A post-regex
            # that silently stops matching looks exactly like one that never ran, which is the
            # whole argument for `post_checks` -- and this rule had none.
            #
            # It also opened a `<span>` it never closed, and left the browser to guess.
            RegexReplacement(
                r'<figcaption(?P<attrs>[^>]*)>(?P<label>[^<:]*?\d+:)\s*(?P<text>.*?)</figcaption>',
                r'<figcaption\g<attrs>><span class="caption-label">\g<label></span> '
                r'<span class="caption-text">\g<text></span></figcaption>',
                purpose="Mark the figure caption's label off from its text",
            ),
            # The authored `style="height:Nmm"` is deliberately left as pandoc wrote it.
            # `core/html/page.py` reads it (`RE_LENGTH`, `size_style`) and turns the height into
            # the width a web page can actually be told, using the drawing's own proportions. A
            # rule here used to rewrite it into `max-height: calc(1.7 * Nmm)` -- a ceiling rather
            # than a size, which is why every picture came out too small, and which would now eat
            # the input `page.py` needs.
        ],
    }

    #: Extensions an `<img>` may still carry once the rules above have run. Anything else is a
    #: picture format with no web rule, which is a build error rather than a broken image on the
    #: page -- the same bargain `\insertPicture` strikes for LaTeX.
    WEB_PICTURE_SUFFIXES = ('svg', 'png', 'jpg', 'jpeg', 'gif', 'webp')

    post_checks = {
        'all': [],
        'html': [
            RegexFailure(r'\\includegraphics', error=r"Caught an unconverted \\includegraphics"),
            RegexFailure(r'\\includesvg', error=r"Caught an unconverted \\includesvg"),
            # A picture format no browser reads. It is the one failure in this family that is
            # silent on the page -- a broken `<img>` shows its alt text and nothing says why --
            # so it is refused here instead of shipped.
            #
            # Looser than the two rewrites above, deliberately: they anchor on `<img src="`,
            # which is what pandoc writes, while this has to catch whatever they did not reach.
            RegexFailure(r'<img[^>]*src="[^"]*\.(tikz|gp)"',
                         error="Caught a picture reference no browser can load: a `.tikz` and a "
                               "`.gp` both become an `.svg` for the web"),
            # Any other picture format with no web rule. This replaces a check that demanded
            # every `src` start with `obrazky/` -- a directory make never created, invented at
            # publish time by `dgs-copy.py` for one website -- which made `.tikz`, `.pdf` and the
            # documented empty-path placeholder all abort an HTML build outright.
            #
            # After the `.tikz`/`.gp` rule above, so the two formats that do have a route to the
            # web keep their own message; this is the catch-all for everything else, and it reads
            # `WEB_PICTURE_SUFFIXES` rather than carrying a second copy of the list.
            RegexFailure(r'<img src="[^"]*\.(?!(?:' + '|'.join(WEB_PICTURE_SUFFIXES) + r')")[A-Za-z0-9]+"',
                         error="Caught a picture in a format the web rules do not convert"),
        ],
        'latex': [
            # Pandoc >= 3.2 wraps an image carrying no attributes in \pandocbounded, a macro that
            # only exists in pandoc's own LaTeX template -- we emit fragments, so it would be
            # undefined at compile time. The cause is always an image without an attribute block,
            # so refuse here rather than defining the macro and rendering an unsized picture.
            RegexFailure(r'\\pandocbounded',
                         error=r"Caught a \pandocbounded: an image has no attributes. "
                               r"Give it a size, e.g. ![caption](picture.svg){height=40mm}"),
            # A crossref label that reached the TeX as literal text, escaped brace and all, so
            # pandoc never read it as an attribute and the thing it names has no label and no
            # number. The cause is always something following the label on its line: pandoc
            # accepts `{#eq:…}` only when whitespace or the end of the block comes next, and
            # `22/hop/hu` printed `{#eq:hop:vxvvxgd}` into the Hungarian booklet for exactly that
            # reason. `settle_display_tags` stops the renderer from creating one; this catches a
            # hand-written one, which no check upstream can see, and refuses the page instead of
            # printing the label.
            RegexFailure(r'\\\{\\#(eq|fig|tbl|sec|lst):',
                         error="A crossref label was typeset as text, so whatever it names has "
                               "no number: nothing may follow `{#eq:...}` on its line"),
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
            RegexReplacement(r"^@T([Oo][Dd][Oo])?\s*(.*)$", r"\\todoMessage{\g<2>}", purpose="Replace TODO tag"),
        ],
        'html': [
            RegexReplacement(r"^@E\s*(.*)$", r"Error: \g<1>", purpose="Replace error tag"),
            RegexReplacement(r"^@T([Oo][Dd][Oo])?\s*(.*)$", r"TODO: \g<2>", purpose="Replace TODO tag"),
        ],
    }

    pre_checks = {
        'all': [
            # Git writes markers of **exactly seven** characters, so the eight this asked for
            # could never match one: the check had never fired, and an unresolved conflict would
            # have gone through into a booklet. These checks run a line at a time, so `^` is the
            # start of the line git puts a marker at, and the trailing `\s|$` is what separates
            # `<<<<<<< HEAD` from seven angle brackets inside a sentence.
            #
            # The `=` arm would also match a seven-character setext heading underline. No source
            # has one -- the whole repository writes ATX `#` headings -- and the other two arms
            # are unambiguous, so drop it rather than loosen the rule if that ever changes.
            RegexFailure(r'^(<{7}|={7}|>{7})(?:\s|$)', error="Git conflict markers present"),
            RegexFailure(r'\^\\circ|\^{\\circ}', error=r"No \circ allowed in exponents"),
            # `@H` and `@L` marked a line as belonging to one output format only. They are gone:
            # no source has ever carried one, in any module, on any branch, in any commit, so
            # there was nothing they kept working and two pairs of rules, two backstops and four
            # tests saying otherwise.
            #
            # Refused rather than dropped, for the reason `-P` now exits argparse: a tag silently
            # ignored reads as though it still worked, and here it would be worse than that --
            # with no rule to consume it the line would simply print, `@L` and all.
            RegexFailure(r'^@[HL]\b',
                         error="`@H` and `@L` have been removed -- they marked a line as "
                               "HTML-only or LaTeX-only, and nothing ever used one. Write the "
                               "line for both formats, or leave it out."),
        ],
        'latex': [],
        'html': [],
    }

    def __init__(self,
                 output_format: str,
                 locale_code: str,
                 infile,
                 outfile,
                 **options):
        self.output_format: str = output_format
        self.locale_code: str = locale_code
        self.locale: i18n.Locale = i18n.languages[locale_code]
        self.infile = infile
        self.outfile = outfile
        self.file = None

        assert output_format in ['html', 'latex'], \
            "Output format is neither 'html' nor 'latex'!"


        (self.quote_open, self.quote_close) = self.locale.data['quotes']['open'], self.locale.data['quotes']['close']

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

        # Spacing rules for `core/filters/spacing.lua`, flattened to strings: the filter has no
        # YAML reader, and three `-M` flags are both enough and visible in the argv when a build
        # is being debugged. The cases are derived here rather than in Lua, whose `string.lower`
        # is byte-oriented and wrong for Cyrillic.
        #
        # Three forms, not two. For a one-letter word `upper()` and `capitalize()` agree, but
        # Ukrainian's list holds two-letter prepositions as well, and a sentence opens with `Із`,
        # not `ІЗ` -- deriving only the upper form left every sentence-initial one unglued.
        typography = self.locale.data.get('typography', {})
        self.nbsp_singles = sorted({
            case
            for word in typography.get('singles', [])
            for case in (word, word.upper(), word.capitalize())
        })
        self.nbsp_pairs = typography.get('nbsp_pairs', [])
        self.thin_pairs = typography.get('thin_pairs', [])
        # Whether `core/filters/hyphens.lua` repeats a hyphen a line breaks at. Passed as a string
        # because `-M` carries strings; absent is false, so a language that declares nothing is
        # unaffected and keeps the plain hyphen it has always had.
        self.repeat_hyphen = bool(typography.get('repeat_hyphen', False))
        # Spanish only: RAE exempts a hyphen followed by a proper noun's capital.
        self.repeat_hyphen_not_before_capital = bool(
            typography.get('repeat_hyphen_not_before_capital', False))

        self.pre_checks = self._filter_regexes(self.pre_checks)
        self.pre_regexes = self._filter_regexes(self.pre_regexes)
        self.post_checks = self._filter_regexes(self.post_checks)
        self.post_regexes = self._filter_regexes(self.post_regexes)

    def _filter_regexes(self, regex_set: dict[str, list]) -> list:
        return regex_set['all'] + regex_set[self.output_format]

    def run(self):
        self.file = self.file_operation(self.pre_check)(self.infile)
        self.in_fence = False           # `outside_code`'s state, which spans lines
        self.file = self.file_operation(self.preprocess)(self.file)
        self.file = self.call_pandoc()
        self.file = self.file_operation(self.postprocess)(self.file)
        if self.output_format == 'latex':
            self.file = self.move_bottom_rules(self.file)
        self.file = self.file_operation(self.post_check)(self.file)
        return self.file.read().rstrip('\n')

    #: A `\bottomrule` on a line of its own, as pandoc emits it inside `\endlastfoot`
    BOTTOMRULE = re.compile(r'^\\bottomrule(\\noalign\{})?\s*$')

    @classmethod
    def move_bottom_rules(cls, f: SpooledTemporaryFile[str]) -> SpooledTemporaryFile[str]:
        r"""
        Move a table's `\bottomrule` out of `\endlastfoot` and into the table body.

        Pandoc puts it in `\endlastfoot`, which longtable's *output routine* inserts when it
        recognises the table's last page. Inside a box -- the tearoff wraps every problem in
        fixed-height minipages -- there is no page breaking and no output routine, so the foot
        is never consulted and the rule silently disappears. Emitting no-ops after the table
        does not help: nothing is queued, the foot is simply unused. As the last row of the
        body the rule is an ordinary `\noalign` between rows and always prints.

        Needs one line of lookahead, hence a buffered pass rather than a `post_regexes` entry.
        """
        out = SpooledTemporaryFile(mode='w+')
        held: str | None = None         # a \bottomrule whose fate depends on the next line
        deferred = False                # this table's rule has to be re-emitted before its end
        for line in f:
            if held is not None:
                if line.startswith(r'\endlastfoot'):
                    deferred = True     # drop the held rule, it belongs to the unused foot
                else:
                    out.write(held)     # a rule anywhere else stays exactly where it was
                held = None
            if cls.BOTTOMRULE.match(line):
                held = line
                continue
            if line.startswith(r'\end{longtable}') and deferred:
                out.write('\\bottomrule\\noalign{}\n')
                deferred = False
            out.write(line)
        if held is not None:
            out.write(held)
        out.seek(0)
        return out

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

    #: The two boxes the renderer leaves in the Markdown, and what they become on the web.
    #:
    #: A word the language has not got arrives here as a literal `\errorMessage{and:cs}`, not as
    #: a tag -- `@E` has already been handled by `pre_regexes`. Pandoc drops raw LaTeX when it
    #: writes HTML, so without this the box is not merely unstyled on the web, it is **gone**,
    #: and the hole it exists to mark reads as a missing space. That is volume 19's `onion` in
    #: another medium, and this box is the one thing that must never be silent.
    #:
    #: Raw inline HTML is passed through by pandoc's Markdown reader. The colour is written
    #: inline because a fragment has no stylesheet of its own: it is dropped into whatever page
    #: consumes it, and a class alone would leave the box invisible there.
    BOXES = (
        (re.compile(r"\\errorMessage\{([^{}]*)\}"),
         (r'<span class="dgs-error" style="background:#c00;color:#fff;'
         r'padding:0 .25em;border-radius:2px">\1</span>')),
        (re.compile(r"\\todoMessage\{([^{}]*)\}"),
         (r'<span class="dgs-todo" style="background:#fe6;color:#000;'
         r'padding:0 .25em;border-radius:2px">\1</span>')),
    )

    #: An inline code span. Markdown sets one verbatim, so a macro written in one is being
    #: *named* rather than called.
    CODE_SPAN = re.compile(r'`+[^`]*`+')
    #: A fenced block's delimiter, which toggles the same protection across several lines.
    FENCE = re.compile(r'^\s{0,3}(?:`{3,}|~{3,})')

    def preprocess(self, line):
        # return self.chain_process(line, [self.pre_regexes, self.quotes_regexes]) # Turned off for quote testing!
        line = self.chain_process(line, [self.pre_regexes])
        if self.output_format == 'html':
            # siunitx is expanded into ordinary TeX for the web, because MathJax has no siunitx
            # and the macro shims people reach for cannot parse an argument -- a list, an angle
            # in `d;m;s` form and an exponent all need one. A function and not a `pre_regexes`
            # entry for the same reason: this is a small parser, not a substitution.
            # See `core/filters/siunitx`.
            #
            # The same goes for this repository's own parsed macros one step further on:
            # `\Int[0][T]{v}{t}` and `\FDiff^{2}_{\text{vap}}{H}` are shapes no fixed-arity
            # MathJax macro can take. The fixed-arity half stays a macro, in `mathjax-dgs.js`.
            line = self.outside_code(line, self.expand_for_the_web)
        return line

    def expand_for_the_web(self, prose: str) -> str:
        """Everything the web needs rewritten, over one stretch of prose that is not code."""
        prose = dgsmacros.expand(siunitx.expand(prose, self.locale))
        for pattern, replacement in self.BOXES:
            prose = pattern.sub(replacement, prose)
        return prose

    def outside_code(self, line: str, expand: Callable[[str], str]) -> str:
        r"""
        `expand` applied to the prose of a line and to nothing else.

        Markdown sets a code span and a fenced block verbatim, so a macro written in one is being
        *named*, not called: `source/naboj/phys/errors/*.md` is prose *about* the sources and
        names `\qty` and `\Diff` throughout, and `test/00`'s macro problems print each call in a
        `<code>` beside its own rendering. Expanding there replaces the thing being talked about
        with its answer, which is the one place the answer is not wanted.

        The TeX writer never gets here, because neither expander runs for it.
        """
        if self.FENCE.match(line):
            self.in_fence = not self.in_fence
            return line
        if self.in_fence:
            return line
        out, i = [], 0
        for span in self.CODE_SPAN.finditer(line):
            out.append(expand(line[i:span.start()]))
            out.append(span.group())
            i = span.end()
        out.append(expand(line[i:]))
        return ''.join(out)

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
            "--columns=200",
            "--wrap=preserve",
            "--filter", "pandoc-crossref",
            "-M", f"crossrefYaml=build/core/i18n/{self.locale_code}.yaml",
            "--lua-filter", "./core/filters/quotes.lua",
            "--lua-filter", "./core/filters/spacing.lua",
            "-M", "nbsp-singles=" + ' '.join(self.nbsp_singles),
            "-M", "nbsp-pairs=" + ';'.join(self.nbsp_pairs),
            "-M", "thin-pairs=" + ';'.join(self.thin_pairs),
            # After `spacing.lua`, which inserts U+00A0 and U+202F into `Str` nodes. Order does
            # not actually matter here -- one rule looks at spaces, the other at hyphens -- but
            # keeping the typography filters together and in a fixed order makes the argv readable.
            "--lua-filter", "./core/filters/hyphens.lua",
            "-M", f"repeat-hyphen={'true' if self.repeat_hyphen else 'false'}",
            "-M", ("repeat-hyphen-not-before-capital="
                  f"{'true' if self.repeat_hyphen_not_before_capital else 'false'}"),
        ]
        if self.output_format == 'html':
            # `--math-method`, not the `--mathjax` flag, which pandoc 3 deprecates with a warning
            # on every single file. It is what makes pandoc leave a formula alone in a
            # `<span class="math">` instead of trying to render it.
            #
            # **Nothing here is engine-specific, deliberately.** A fragment keeps the formula the
            # author wrote, so the same `build/**.html` serves both ways of setting it -- the
            # xelatex one and the MathJax one -- and choosing between them costs a page rebuild
            # rather than a pandoc rebuild. `core/html/page.py` is where the choice is made.
            args += [
                "--math-method=mathjax",
                # Raw LaTeX in prose, which the HTML writer drops without a word. Not about
                # either engine and not a duplicate of `expand_for_the_web`: that one expands
                # what it knows -- siunitx and this repository's own macros -- and everything
                # else, mhchem's `\ce` above all, is still a `RawInline` that pandoc throws
                # away. `chem/01/robinson` asked its reader for "prikvapkaný jeden ekvivalent ."
                # with the reagent simply gone.
                "--lua-filter", "./core/filters/rawtex.lua",
            ]

        # `check=True` alone raises `returned non-zero exit status 83` and nothing else, so a
        # filter that stopped the build on purpose loses the one sentence that says what to do
        # about it. Capture stderr and put it in the exception.
        completed = subprocess.run(args, stdin=self.file, stdout=out, stderr=subprocess.PIPE,
                                   text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"pandoc failed on {getattr(self.infile, 'name', '<stdin>')}:\n"
                               f"{completed.stderr.strip()}")
        if completed.stderr.strip():
            print(completed.stderr, end='', file=sys.stderr)

        out.seek(0)
        return out
