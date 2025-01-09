This is DGS, short for Document Generation System (pronounced ['degeʃ]).

DGS is a build system for structured documents, mostly those built on standardized
frameworks, where the structure is always the same (or very similar) but the underlying
data change -- such as correspondence seminar problems, competitions, lectures,
homework sheets and handouts. It also includes basic internationalization.

The same content can be repeatedly rendered to various templates or output formats,
for instance XeLaTeX for printable documents and HTML for the web.
DGS is built with Makefile, Python and XeLaTeX, and uses `pandoc` and `rsvg-convert`
to process content.
