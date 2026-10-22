import re


class Picture:
    r"""
    A figure declared once in `pictures:` and included as `(§ pictures.<key> §)`.

    The three parts of a Markdown include that are facts about the *drawing* -- which file, how
    big, and what it is called -- live in the meta, so they are written once instead of once per
    language. What stays at the call site is the caption, which is prose and must be translated,
    and the position, which a translator may legitimately move.

    This is the figure half of what `MathObject` does for an equation, and the argument is the
    same one: **the key is the label**. Nobody types `{#fig:<pid>:<key>}`, so nobody can misspell
    it -- 440 of the repository's 869 hand-written figure labels did not follow the convention,
    against about 1 % on the equation side, and a wrong figure label is silent until a crossref
    resolves to nothing.
    """
    def __init__(self,
                 ident: str,
                 file: str,
                 *,
                 captioned: bool = True,
                 caption: str | None = None,
                 declared_caption: str | None = None,
                 attributes: dict | None = None):
        self.id = ident
        self.file = file
        #: A caption written in the meta rather than at the call site, already resolved for this
        #: language by `build_render_context`.
        #:
        #: The call site is the right place for a caption and stays the normal one: it is prose,
        #: only 5 of 386 are the same in every language, and a translator may want it to read
        #: differently. This is for the one case the call site cannot express -- **a caption that
        #: interpolates**. A caption is passed as a string argument, and a `(§ … §)` inside a
        #: string literal ends the enclosing tag at its first `§)`, so
        #: `(§ pictures.x('… $(§ Imax §)$') §)` does not parse at all.
        #:
        #: Here it needs no quoting, because nothing lexes it: the text is emitted into the
        #: Markdown as written and the *next* render pass expands whatever tags it holds. That is
        #: how `blocks:` works, and it is the same reason -- `render_to_fixpoint` keeps going
        #: until the output stops changing.
        self.declared_caption = declared_caption
        #: Whether this file's figures carry a caption, and therefore a number and a label.
        #:
        #: Set by the renderer from the file being rendered against the module's own
        #: `figure_captions`, never by the author at the call site -- the same decision, made in
        #: the same place and for the same reason, as `MathObject.labelled`.
        #:
        #: **A problem statement never captions its figures**, so they are never numbered. The
        #: number would be a cross-reference a contestant cannot follow, and the measurement says
        #: nobody wanted one anyway: 169 distinct labels are defined in statements across the
        #: repository and not one of them is referenced from anywhere.
        #:
        #: **A solution always does**, even where the caption is empty, because that is what makes
        #: the figure numbered -- and a figure that is numbered in one language and not in another
        #: is how `18/firework-bee` came to print `??` in the English booklet alone.
        self.captioned = captioned
        self.caption = caption
        self.attributes = dict(attributes or {})

    #: What goes between `![` and `]` when a solution's figure has no caption of its own.
    #:
    #: Not the empty string and not a space: pandoc makes a `figure` environment only when the alt
    #: text has content, so `![]` and `![ ]` both come out as a bare `\includegraphics` with no
    #: number and no `\label` -- which is exactly the state this rule exists to end. An HTML
    #: comment is content to the parser and nothing to the page, so the figure is numbered and the
    #: caption prints empty.
    EMPTY_CAPTION = '<!-- -->'

    def __call__(self, caption: str | None = None, **attributes) -> Picture:
        """
        The same picture with a caption, or with an attribute overridden at this call site.

        An override is meant to be rare and visible. The size lives in the meta because 166 of the
        386 multilingual figures in the repository disagree about it by accident -- the same
        drawing at 14 mm, 35 mm and 55 mm in three booklets -- but it cannot be forced, because a
        tear-off has a fixed height and translations do not have equal line counts. So the meta
        carries what the languages agree on and `(§ pictures.x(height='55mm') §)` says, in one
        place a reader can see, that this one is different on purpose.
        """
        return Picture(self.id, self.file,
                       captioned=self.captioned,
                       caption=self.caption if caption is None else caption,
                       declared_caption=self.declared_caption,
                       attributes=self.attributes | attributes)

    @property
    def _label(self) -> str:
        """
        The label, where the figure is captioned, and nothing where it is not.

        Nothing rather than a label is not a simplification. An uncaptioned image is not a
        `figure` at all, so pandoc emits no `\\label` for it whatever the attribute block says --
        553 of the repository's hand-written labels sit on uncaptioned images and reach the page
        as nothing. Emitting one here would be writing markup that is known to be discarded.
        """
        return f"#fig:{self.id}" if self.captioned else ""

    def _attribute_text(self) -> str:
        return ' '.join(f"{key}={value}" for key, value in self.attributes.items())

    @staticmethod
    def _one_line(caption: str) -> str:
        r"""
        A caption wrapped across several source lines, emitted on one.

        The wrapping belongs to the source, where a long line is a real cost -- the 120-character
        limit, a diff nobody can read -- and it buys nothing in the output: a newline inside
        `![…]` is a space to pandoc, and the `\caption{}` it writes sets identically either way.
        Encoding the break instead, as a `\n` in the Jinja string, got this exactly backwards:
        it put the break where it does nothing and the long line where it hurts, and 21 call
        sites came out over 120 characters, the longest at 249.
        """
        # Stripped as well as joined: a `caption:` written as a YAML `|` block keeps its
        # final newline, which would otherwise arrive as a space before the closing `]`.
        return re.sub(r'\s*\n\s*', ' ', caption).strip()

    def __str__(self) -> str:
        """The Markdown include, which the second render pass expands any tags inside."""
        alt = ''
        if self.captioned:
            # The call site first, then the meta, then the marker that makes it a numbered figure
            # with nothing written in it.
            written = self.caption if self.caption else self.declared_caption
            alt = self._one_line(written) if written else self.EMPTY_CAPTION
        attributes = ' '.join(part for part in (self._label, self._attribute_text()) if part)
        # The attribute block is never omitted even when it is empty: `convertor.py` refuses an
        # image that reaches LaTeX without one -- `RegexFailure(r'\\pandocbounded')` -- because an
        # unsized figure is set at its natural size and walks off the page.
        return f"![{alt}]({self.file}){{{attributes}}}"

    def __repr__(self) -> str:
        return repr(self.__str__())
