# Reading the ancient Náboj archive

`source/naboj/fks-naboj/.ancient/` holds the Náboj years the current system never received —
2007 and 2009–2015, which are volumes 10 and 12–18 (volume = year − 1997, and each year states
its own ročník in `uvod.tex`). This directory holds the tools for converting them.

## `reference.tex` — read a year as it was printed

**The archive does not build, and has not for years.** Three things stop it:

- `cslatex` is gone from TeX Live, and `include.tex` opens with `\let\pdfpagewidth=\undefined`,
  a dvips-era hack that sends `geometry` into an infinite loop under any modern engine.
- `\usepackage{slovak}` is a direct language-style load, which modern babel refuses outright.
- The `.eps` figures are **build products**. The old `Makefile` generated them from the `.svg`
  with an Inkscape wrapper (`install/svg2eps`), and none of them are committed.

Rather than resurrect that stack, `reference.tex` is a driver of our own that typesets the
problem bodies so they can be *read*. It reimplements the 2009 dialect — `\unit`, `\mrm`, `\e`,
`\kmh`, `\ms`, `\Ce`, `\sdeg`, `\bodka`, `\ciarka`, `\obrazok`, `\trhaciealt` — and makes no
attempt to reproduce the booklet's layout.

```sh
S=$(mktemp -d)
cp -r source/naboj/fks-naboj/.ancient/2009/ulohy/. "$S"/
cp tools/ancient/reference.tex "$S"/
cd "$S" && for f in */*.svg; do
    inkscape --export-text-to-path --export-type=eps --export-filename="${f%.svg}.eps" "$f"
done
xelatex -interaction=nonstopmode reference.tex && xelatex -interaction=nonstopmode reference.tex
```

2009 comes out at 23 pages, all 46 problems, zero errors.

**Two things it deliberately does not reproduce.** `mathab.sty` makes `.` active in maths and
prints it as a decimal comma; this driver leaves it a period. That costs nothing for reading the
physics, and the modern pipeline renders a `.` in the source as a comma in Slovak output anyway
(`core/i18n/sk.yaml`), so the printed result agrees at both ends. It also leaves `"` inert, where
`typoconv.sty` made it an active Slovak quote pair.

**Three macros in the archive are used and never defined** — `\matheq`, `\mathplus` and
`\mathminus`, across five 2009 files. `mathab.sty` makes `=`, `+` and `-` active, and these were
plainly meant to be the saved originals, but no shipped version of `mathab.sty` defines them.
The driver defines them as the plain characters, which is what they must have meant.
