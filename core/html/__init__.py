r"""
What the HTML output needs that the LaTeX output gets from a package.

There are two ways to put maths on the page, and this is where the choice is made.

**`latex`** hands every formula to the xelatex that sets the booklet and inlines the SVG it
gives back (`texmath.py`, `core/templates/mathpage.jtex`). It is the booklet's typeface and the
booklet's `math.tex`, and chemfig is drawn rather than approximated.

**`mathjax`** typesets under node instead (`mathjax.py`). It gives selectable, searchable text
and a smaller page, in a different typeface from the printed one.

**Neither of them rewrites anything.** MathJax has mhchem and knows nothing whatever about
siunitx -- no extension for it exists -- and cannot express most of `math.tex`, whose macros
are `\NewDocumentCommand`s with embellishment and delimited arguments; but that expansion
happens in `Convertor.expand_for_the_web`, before pandoc, through `core/filters/siunitx.py`
and `dgsmacros.py`. A fragment reaching this package holds plain maths, which both engines
read, so one pandoc build still serves both and switching costs a page rebuild.

The cost of expanding that early falls on the `latex` engine, which would have been happy with
`\qty`: what xelatex sets is our expansion of it rather than siunitx's own. `test_siunitx.py`
holds the two together by comparing against compiled siunitx.

`page.py --maths latex|mathjax` chooses per page; `ENGINE` below is only the default.
"""

#: Which engine a page gets when nothing says otherwise. `page.py --maths` overrides it.
ENGINE = 'latex'
