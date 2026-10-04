r"""
What the HTML output needs that the LaTeX output gets from a package.

There are two ways to put maths on the page, and this is where the choice is made.

**`latex`** hands every formula to the xelatex that sets the booklet and inlines the SVG it
gives back (`texmath.py`, `core/templates/mathpage.jtex`). The maths then *is* the booklet's
maths -- MinionPro, siunitx's own spacing, `math.tex`'s macros, chemfig -- and the shims below
are not in the way of it.

**`mathjax`** typesets under node instead (`mathjax.py`). MathJax has mhchem and knows nothing
whatever about siunitx -- no extension for it exists -- and cannot express most of `math.tex`,
whose macros are `\NewDocumentCommand`s with embellishment and delimited arguments. So that
route needs shims, and they are *generated from the LaTeX* wherever they can be, because a
second hand-written copy of a unit table is a second thing to keep in step: `macros.py` reads
`math.tex` and writes `core/filters/macros-table.lua`, `siunitx.py` reads `siunitx.tex` and
writes `core/filters/siunitx-table.lua`. It gives selectable, searchable text and a smaller
page, and it is a different typeface from the printed one.

**Nothing upstream of the page knows which it is.** `build/**.html` holds the formula the
author wrote -- `\qty`, `\FDiff`, chemfig and all -- and the shims run inside `mathjax.py`
rather than in the convertor, so one pandoc build serves both engines and switching between
them costs a page rebuild. That is also what makes the two comparable: the same fragments, set
two ways.

`page.py --maths latex|mathjax` chooses per page; `ENGINE` below is only the default.
"""

#: Which engine a page gets when nothing says otherwise. `page.py --maths` overrides it.
ENGINE = 'latex'
