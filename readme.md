This is DGS, short for Document Generation System (pronounced ['degeʃ]).

DGS is a compositor for structured documents, mostly those built on standardized frameworks,
where the structure is always the same (or very similar) but the underlying data change.
It was primarily built for correspondence seminar problems, real-time competitions,
lectures, homework sheets and handouts for university courses.
It also includes basic internationalization.

The same content can be repeatedly rendered to various templates or output formats,
for instance XeLaTeX for printable documents and HTML for the web.
DGS is built with Makefile, Python and XeLaTeX, and it uses
`pandoc`, `jinja2`, `rsvg-convert`, and `dvisvgm` to process content.

The authors would like to express their gratitude to

- Joseph Wright, for the wonderful `siunitx` package, which has made our life orders of magnitude easier
- Christian Tellechea for `chemfig`, which allowed Náboj Chemistry to escape the Microsoft hell
- Sebastian Schubert for `FontPro`, which did the same for the seventh circle of Computer Modern
