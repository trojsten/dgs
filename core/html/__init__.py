"""
What the HTML output needs that the LaTeX output gets from a package.

The PDF path hands `siunitx`, `mhchem` and `core/latex/math.tex` to xelatex and is done. The web
has MathJax, which has mhchem and knows nothing whatever about siunitx -- no extension for it
exists -- and cannot express most of `math.tex`, whose macros are `\\NewDocumentCommand`s with
embellishment and delimited arguments.

So the shims live here, and they are *generated from the LaTeX* wherever they can be, because a
second hand-written copy of a unit table is a second thing to keep in step.
"""
