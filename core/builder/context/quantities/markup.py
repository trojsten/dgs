r"""
How an equation and a figure are *written*, as a choice rather than a hard-coded one.

`backend.py` made the same move for a quantity and says why at length: presentation produced at
the point the value is created is the thing every non-LaTeX consumer has to undo. A `MathObject`
and a `Picture` are the other two values that printed themselves in one markup and no other --
`$$ … $$ {#eq:id}` and `![…](file){…}`, which are Markdown carrying LaTeX, and which mean
nothing to Typst.

**Two axes, one switch.** A quantity's spelling and a document's markup do not vary together:
`PlainBackend` writes `3 m/s` *inside a Markdown document*, because a drawing has no xelatex to
typeset `\qty` with. So the markup hangs off the backend as an attribute rather than being a
second `ContextVar` -- `LATEX` and `PLAIN` both point at `MARKDOWN`, and only `TYPST` points
elsewhere. One thing to set, two things decided, and no way to end up with a Typst figure in a
Markdown file.

What stays in `MathObject` and `Picture` is everything that is not markup: which format specs
exist, what a trailing punctuation mark may attach to, whether a display is labelled, which
caption a figure ends up with. Those are the same questions whatever the page is set in.
"""
import re


class Markup:
    """
    One way of writing a display, an inline fragment, an array and a figure.

    The methods take a *decision* and return a string: `labelled` and `captioned` have already
    been decided by the module's taxonomy, and the caption has already been resolved for the
    language. Nothing here reads a context.
    """
    name: str = None

    def inline(self, content: str) -> str:
        """Maths inside a sentence."""
        raise NotImplementedError

    def display(self, content: str, *, label: str, punctuation: str) -> str:
        """A display block. `label` is this markup's own output from `equation_label`."""
        raise NotImplementedError

    def aligned(self, content: str, *, label: str, punctuation: str) -> str:
        """A display whose rows align on a relation."""
        raise NotImplementedError

    def array(self, content: str, *, columns: str, label: str, punctuation: str) -> str:
        """A display whose columns are specified."""
        raise NotImplementedError

    def equation_label(self, ident: str) -> str:
        """The label an equation carries, or `''` where it carries none."""
        raise NotImplementedError

    def figure(self, *, file: str, ident: str, captioned: bool, caption: str | None,
               attributes: dict) -> str:
        """
        One figure.

        `caption` is `None` when the file's figures are captioned but this one has no text --
        which is still a numbered figure, and the two markups express that differently.
        """
        raise NotImplementedError


class MarkdownMarkup(Markup):
    r"""
    Markdown with LaTeX maths in it: what pandoc reads, and what every source has been until now.

    Every oddity below is something LaTeX needs and nothing else does -- `\jot` on an array's
    row separators, `>{\displaystyle}` on its columns, a `{}` in front of a row that starts with
    a bracket, an HTML comment standing in for an empty caption. They were in `MathObject` and
    `Picture`; they are here so that the other markup does not inherit a single one of them.
    """
    name = 'markdown'

    _COLUMN_TYPES = frozenset('lcr')

    #: What goes between `![` and `]` when a solution's figure has no caption of its own.
    #:
    #: Not the empty string and not a space: pandoc makes a `figure` environment only when the
    #: alt text has content, so `![]` and `![ ]` both come out as a bare `\includegraphics` with
    #: no number and no `\label` -- which is exactly the state the caption rule exists to end. An
    #: HTML comment is content to the parser and nothing on the page.
    EMPTY_CAPTION = '<!-- -->'

    @staticmethod
    def _shield_brackets(content: str) -> str:
        r"""
        Put `{}` in front of a row that starts with `[`.

        LaTeX's `\\` takes an optional length, so a row beginning with a bracket -- a
        concentration `[A]`, an interval, a unit in square brackets -- is read as `\\[A]` and the
        compile dies on `Missing number, treated as zero`. amsmath's `aligned` does not scan for
        that argument and so tolerates it, which is why the problem only appears on the way *in*
        to an array: `01/rovnováha` had written `[A] … \\ [B] …` happily for years.
        """
        rows, out = re.split(r'(?<=\\\\)\n', content), []
        for row in rows:
            stripped = row.lstrip()
            if stripped.startswith('['):
                pad = row[:len(row) - len(stripped)]
                row = f'{pad}{{}}{stripped}'
            out.append(row)
        return '\n'.join(out)

    @staticmethod
    def _open_up_rows(content: str) -> str:
        r"""
        Give every row separator a `\jot` of glue.

        `array` sets `\baselineskip` and `\lineskip` to zero and spaces its rows by a strut
        alone, so two rows whose content is taller than that strut -- which is every row holding
        a display-style `\frac` -- end up touching: in `20/star-triangle` the denominator of one
        row sat directly on the numerator of the next. `aligned` avoids it by doing `\openup\jot`,
        which array ignores because array zeroes the very lengths `\openup` raises. The one lever
        left is explicit glue on the separator.

        `\jot` by name rather than a length of our own, because it is the document's own setting
        for exactly this: the gap between the rows of a display. `dgs.cls` puts it at 10pt, five
        times plain LaTeX's default -- so a fixed length tuned in a scratch document would have
        been wrong in the booklets, and is wrong again the day anyone retunes `\setDisplaySkips`.

        A separator that already carries its own `[…]` is left alone -- the author asked for a
        particular gap.
        """
        return re.sub(r'\\\\(?=\n)', r'\\\\[\\jot]', content)

    @classmethod
    def _display_columns(cls, columns: str) -> str:
        r"""
        Put every column of an array in display style.

        `array` sets its cells in **text** style, so a `\frac` inside one comes out at script
        size -- next to an `aligned` block on the same page the difference is glaring. `array`'s
        `>{…}` prefix fixes it per column, and that prefix is an `array` package feature --
        reaching the document indirectly, through `\RequirePackage[table]{xcolor}` in `dgs.cls`,
        which loads `colortbl`, which loads `array`. Drop that `table` option and this breaks.
        """
        return ''.join(f'>{{\\displaystyle}}{c}' if c in cls._COLUMN_TYPES else c
                       for c in columns)

    @staticmethod
    def _indent(content: str, spaces: int) -> str:
        return re.sub(r'^(?!\Z)', ' ' * spaces, content, flags=re.MULTILINE)

    def equation_label(self, ident: str) -> str:
        return f" {{#eq:{ident}}}"

    def inline(self, content: str) -> str:
        return f"${content}$"

    def display(self, content: str, *, label: str, punctuation: str) -> str:
        return f"$$\n{self._indent(content, 4)}{punctuation}\n$${label}"

    def aligned(self, content: str, *, label: str, punctuation: str) -> str:
        r"""
        `\begin{aligned}` where `disp`'s content would be, and the rows inside it.

        This used to emit the `$${ … }$$` shorthand and leave `Convertor.pre_regexes` to rewrite
        it into exactly this on the way to pandoc. Two per-line regexes for a form nothing else
        wanted; the filter knows what it means, so it says it. The regexes stay for the 351
        `$${` that authors still write by hand.
        """
        return (f"$$\n    \\begin{{aligned}}\n"
                f"{self._indent(content, 8)}{punctuation}\n"
                f"    \\end{{aligned}}\n$${label}")

    def array(self, content: str, *, columns: str, label: str, punctuation: str) -> str:
        """
        The punctuation lands **inside the final cell**, where it belongs.

        After `\\end{array}` it would float at the array's vertical centre, beside the middle row.
        """
        body = self._open_up_rows(self._shield_brackets(content))
        return (f"$$\n    \\begin{{array}}{{{self._display_columns(columns)}}}\n"
                f"{self._indent(body, 8)}{punctuation}\n"
                f"    \\end{{array}}\n$${label}")

    def figure(self, *, file: str, ident: str, captioned: bool, caption: str | None,
               attributes: dict) -> str:
        """
        The Markdown include, whose tags the second render pass expands.

        The attribute block is never omitted even when it is empty: `convertor.py` refuses an
        image that reaches LaTeX without one -- `RegexFailure(r'\\pandocbounded')` -- because an
        unsized figure is set at its natural size and walks off the page.
        """
        alt = ''
        if captioned:
            alt = caption if caption else self.EMPTY_CAPTION
        # An uncaptioned image is not a `figure` at all, so pandoc emits no `\label` for it
        # whatever the attribute block says -- 553 of the repository's hand-written labels sit on
        # uncaptioned images and reach the page as nothing. Emitting one would be writing markup
        # that is known to be discarded.
        label = f"#fig:{ident}" if captioned else ""
        written = ' '.join(f"{key}={value}" for key, value in attributes.items())
        block = ' '.join(part for part in (label, written) if part)
        return f"![{alt}]({file}){{{block}}}"


class TypstMarkup(Markup):
    r"""
    Typst, where the markup is the typesetting language and nothing converts between them.

    Three things are simply smaller here, and each is a LaTeX workaround that has no counterpart:

    - **a label is Typst's own** -- `<eq:id>` after the display, and `@eq:id` refers to it, with
      the reference's word taken from `#set text(lang:)`. `{#eq:…}` exists because Markdown has
      no labels and pandoc-crossref had to invent them;
    - **alignment needs no environment.** Typst's display maths aligns on `&` and breaks rows on
      `\` by itself, so `aligned` is `display` -- the `\begin{aligned}` wrapper is amsmath's
      requirement, not a statement about the equation;
    - **an empty caption is `[]`**, a figure with nothing written in it, so the HTML-comment
      trick is not needed. An *uncaptioned* figure is a bare `#image`, which is unnumbered and
      unlabellable -- the same distinction the Markdown side draws, expressed directly.
    """
    name = 'typst'

    def equation_label(self, ident: str) -> str:
        return f" <eq:{ident}>"

    def inline(self, content: str) -> str:
        """
        No space after the opening `$`, which is what makes it inline rather than a display.

        That is Typst's whole rule for the distinction, so the content is stripped: a fragment
        hoisted into `eq:` as a YAML block scalar brings a newline that would silently turn an
        inline reference into a display.
        """
        return f"${content.strip()}$"

    def display(self, content: str, *, label: str, punctuation: str) -> str:
        return f"$\n{content}{punctuation}\n${label}"

    def aligned(self, content: str, *, label: str, punctuation: str) -> str:
        """Typst aligns on `&` inside any display, so this is `display` and says so."""
        return self.display(content, label=label, punctuation=punctuation)

    def array(self, content: str, *, columns: str, label: str, punctuation: str) -> str:
        """
        Deliberately refused rather than approximated.

        `|arr` exists because LaTeX's `aligned` pairs its columns `rl rl` and cannot set a chain
        of two relations straight; Typst's display maths has no such limitation, so the right
        answer in a Typst source is `|align` with `&` where the columns should line up. A
        silently different layout would be worse than a message.
        """
        raise NotImplementedError(
            "`|arr` has no Typst spelling: Typst's display maths aligns on `&` directly, so "
            "write `|align` and put a `&` at each alignment point. The column spec "
            f"{columns!r} is a LaTeX `array` requirement and has no counterpart."
        )

    @staticmethod
    def _attributes(attributes: dict) -> str:
        """`height=40mm` becomes `, height: 40mm` -- Typst's own named arguments."""
        return ''.join(f", {key}: {value}" for key, value in attributes.items())

    def figure(self, *, file: str, ident: str, captioned: bool, caption: str | None,
               attributes: dict) -> str:
        image = f'image("{file}"{self._attributes(attributes)})'
        if not captioned:
            return f"#{image}"
        return f"#figure({image}, caption: [{caption or ''}]) <fig:{ident}>"


MARKDOWN = MarkdownMarkup()
TYPST = TypstMarkup()
