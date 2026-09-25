This is DGS, short for Document Generation System (pronounced ['degeʃ]).

DGS is a compositor for structured documents, mostly those built on standardized frameworks,
where the structure is always the same (or very similar) but the underlying data change.
It was primarily built for correspondence seminar problems, real-time competitions,
lectures, homework sheets and handouts for university courses.
It also includes basic internationalization.

The same content can be repeatedly rendered to various templates or output formats,
for instance XeLaTeX for printable documents and HTML for the web.
DGS is built with Makefile, Python, Markdown and XeLaTeX, and it uses
`pandoc`, `jinja2`, `rsvg-convert`, and `dvisvgm` to process content.

The authors would like to express gratitude to

- John Gruber, for creating Markdown, without which the entire project would not be worth developing;
- Armin Ronacher, for the Jinja2 template engine, that makes composing documents practical, if not enjoyable;
- Joseph Wright, for the wonderful `siunitx` package, which has made our life with LaTeX orders of magnitude easier;
- Christian Tellechea for `chemfig`, which allowed Náboj Chemistry to escape the Microsoft hell;
- Sebastian Schubert for `FontPro`, which did the same for the seventh circle of Computer Modern.
- Hernan Grecco for `pint`, which finally solved the long-standing problems of physics templating.

## Installing

There is a container, which is the short way: `sudo apt install podman`, then
`./dgs-container build && ./dgs-container editor`. Otherwise see [install.md](install.md). The toolchain comes in three tiers and you probably do not need all
of them: editing, rendering Markdown and the `/audit` page cost a `pip install`, while TeX needs
pandoc and only the PDF needs TeX Live and the MinionPro build. The editor greys out whatever this
machine cannot do and says what would fix it; `uv run python tools/editor/capabilities.py` reports
the same thing from the command line.

Note that a fresh clone has an **empty `source/`**: the content lives in separate repositories
that are not submodules of this one, so there is no `git submodule` step. install.md lists them,
and so does the editor when it finds nothing to edit.

