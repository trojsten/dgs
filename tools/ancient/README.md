# Reading the ancient Náboj archive

`source/naboj/fks-naboj/.ancient/` holds the Náboj years the current system never received —
2007 and 2009–2015, which are volumes 10 and 12–18 (volume = year − 1997, and each year states
its own ročník in `uvod.tex`). This directory holds the tools that converted them. **All eight
are in the tree now**; 2008 exists nowhere, and volume 11 is the hole that leaves.

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

## `convert.py` — a year of the archive as a draft volume

```sh
uv run python -m tools.ancient.convert --year 2009 --volume 12 \
    --ancient source/naboj/fks-naboj/.ancient/2009/ulohy \
    --slugs   tools/ancient/slugs/2009.yaml \
    --out     /tmp/draft/12
```

It **never writes into `source/`**. The draft goes to `--out`, and moving it into the tree is a
separate, visible step, so hand-finishing in the real tree can never be clobbered by a re-run.
Review one with `diff -ru <out>/problems/<pid> source/naboj/phys/<vol>/problems/<pid>`.
`--dry-run` writes only the report, which is how you point it at the next year and find out what
the rule table is missing before committing to it; `--only DIR/slug.tex` does one problem.

### Two kinds of rule, and the distinction is the whole design

**Silent rules have one right answer.** `\mrm{x}` is `\text{x}`, `v~ktorom` is `v\ ktorom`,
`{a \over b}` is `\frac{a}{b}`, `\varepsilon` is `\epsilon` because `mdcheck` says so. These are
applied and not mentioned.

**Reported rules do not.** Whether a display ends a sentence, whether `\tfrac{2}{3}` wants
`\frac` or `\TwoThirds`, which part of an evaluator's note is the answer — only the sentence
decides, and a converter that picked would be inventing. Those leave the source as it stands and
add a `%# TODO(rule)` line, which is Jinja's own comment prefix: stripped before pandoc,
invisible in the PDF, and greppable. **The conversion is not finished while one remains** —
`grep -rn '%# TODO' source/naboj/phys/<vol>/` is the gate.

**Nothing from `mathab.sty` survives into the output.** Every one of its macros is expanded into
either plain maths or a DGS macro; none is carried across and none is redefined on the DGS side.
The new tree should not inherit a 2009 dialect.

### The dialect is read from the year, never hard-coded

`\obrazok` changes arity *and* argument order across the archive — two arguments in 2009, four in
2010–2013 with the label third, five in 2014–2015 with caption and label swapped, and in 2007 no
`\obrazok` at all, only a bare `\includegraphics` — and `\kmh` is
`km / h` in `mathab.sty` but `km\,h^{-1}` in 2009's own `include.tex`, which is loaded later and
wins. One regex across seven years would silently transpose captions into labels and print wrong
units. `dialect.py` parses the year's `include.tex`, **asserts** the arity against a per-year
descriptor, and aborts on a year the table does not cover. 2007 has no style file at all — its
four macros are defined inside each of the five driver documents — so `Dialect.MACROS` names
`07naboj.tex` for it.

**2007 is the one year with its own code path**, and it earns it: there is no `priklady.tex`
list of `\priklad{}` includes, because `07priklady.tex` *is* the problems, one
`\zadanie`/`\vzorak`/`\comment` group after another. `--monolith` makes a problem's key its
position in that file and `--encoding iso-8859-2` reads it:

```sh
uv run python -m tools.ancient.convert --year 2007 --volume 10 \
    --ancient   source/naboj/fks-naboj/.ancient/2007 \
    --monolith  07priklady.tex --encoding iso-8859-2 \
    --slugs     tools/ancient/slugs/2007.yaml --out /tmp/draft/10
```

Its notation is pre-`\unit{}` throughout: a quantity is a medium space, one upright box per
factor and a full stop between them (`$120\:\mathrm{km}.\mathrm{h}^{-1}$`), a decimal marker is
`4,\!2`, and the file holds not one `~`, so nothing gave its one-letter prepositions a
non-breaking space. `rules.spaced_units` and `rules.thin_comma` handle the first two; the third
is a volume-level pass, since which words take a tie is the year's convention and not a
sentence's.

### Four traps that cost real time, all of them silent

Each of these produced a clean exit code and wrong output, and each is now a rule with a test
case in its docstring:

- **A magnitude has digit groups and may be an exponent.** `0.133\,33\unit{rad}` matched only the
  final `33`; `10^5\unit{Pa}` attached the unit to the exponent. Both *found* a magnitude, so
  neither was reported.
- **`\b` is not how a TeX control word ends.** `\matheq2\pi` has no word boundary between `q` and
  `2`, so the whole sweep missed it. Every macro pattern ends `(?![a-zA-Z])`.
- **A brace group is not found by scanning backwards.** `over_to_frac` took the nearest `{` behind
  the `\over`, which is the wrong one whenever the numerator closed a group of its own —
  `{\bigl(...\tfrac{1}{2}M\bigr)g \over \sin\alpha}` — and the loop then never terminated.
- **A bare decimal in maths prints the wrong separator.** The archive made `.` active and printed
  a comma; today only siunitx does, so `$0.8c$` must become `$\num{0.8}c$`. Found by reading the
  built booklet, by no check.

### `figures.py` — the drawings

Every archive SVG names TeX fonts that are not installed, and `fc-match cmmi12` answers *Noto
Sans*, so a figure converts with a clean exit and its labels come out upright where they should
be italic. The repair is a style rewrite, because the text is already correct Unicode. Two rules
read the label rather than its font: Symbol-encoded Greek (a `Mathematica1` `a` is α, and
rewriting only the family would turn it into a Latin `a`), and a single maths variable in any
foreign font, which moves to Minion Pro with the slant LaTeX would give it. A foreign font on
anything longer stays — a sentence in `Reprise Script` is a design choice.

**Metrics are the residual risk.** Minion is narrower than cmmi and these labels are absolutely
positioned, so a label centred on an arrowhead can drift. Look at the result; a clean exit proves
nothing. Render a contact sheet:

```sh
for f in <out>/problems/*/*.svg; do rsvg-convert -z 2 -b white -o "$(basename "$f" .svg).png" "$f"; done
montage *.png -tile 4x -geometry +6+6 contact.png
```

### `outlines.py` — a figure whose labels were outlined

`_from_eps` says so when it happens: an EPS that embeds its fonts as Type 1 subsets **with no
ToUnicode map** tells nothing downstream what a glyph is, so `mutool` writes a row of U+FFFD and
`pdftocairo` writes outlines, and the outlines ship because they at least draw the right
picture. 2007 is the whole of that problem today — all 21 of its figures are CorelDRAW 11
exports and every one lost its text this way.

The outlines are recoverable, because `pdftocairo` is tidy: it defines each distinct shape once
as `<g id="glyph-1-0">` and places it at a baseline with `<use x= y=>`. So a table naming the
shapes turns every placement into a `<text>` at coordinates the drawing already uses, and
nothing moves.

```sh
uv run python -m tools.ancient.outlines --year 2007 source/naboj/phys/10/problems
```

`glyphs/2007.yaml` is that table: 92 shapes across 19 figures, read once off a rendered sheet of
them all. Each entry is `[character, style, size]`, where the style is `i` for a variable, `u`
for a digit, a unit, an operator or a degree sign, and `-` to leave the shape outlined — which
is right for an accent, since the arrow of a `\vec{F}` belongs to the drawing rather than to the
label. Figures are matched by a fingerprint of their own outlines rather than by filename,
because a figure reaches the tree under the role it plays and has lost the archive's name by
then.

Build the sheet the same way the contact sheet above is built: render each `<g id="glyph-…">`
on its own, montage them in order, and read them in one sitting.

### `compose.py` — two drawings, one figure

Where the archive sets two drawings side by side with plain TeX between them and labels them in a
`\par` underneath, Markdown has no equivalent: two `![](...)` are two figures, free to break
across a page, and only one can carry the label the prose points at.

```sh
uv run python -m tools.ancient.compose --gap 45 --labels '(1)' '(2)' \
    -o bat-echo-solution.svg netopier-ries1.svg netopier-ries2.svg
```

Nested `<svg>`, not a transform, so each drawing keeps its own coordinate system. Three things it
has to do that are not obvious, each of which showed up as a broken render: hoist the children's
namespace declarations onto the wrapper, prefix every internal id per pane (panes saved from one
drawing share ids, and references then resolve to the wrong pane), and clip each pane with an
explicit `clipPath`, since librsvg honours neither the implied nor an explicit `overflow`.

## Converting a year: the order that worked

1. Reference build, so there is something to check the transcription against.
2. Volume skeleton — `meta.yaml` in `priklady.tex` order, `languages/<lang>/`, and `errors/<vol>.md`
   started on day one, because the findings arrive faster than they can be remembered.
3. The rule table against **one** problem, then frozen.
4. Figures in one batch, reviewed in one sitting rather than 22 interruptions.
5. Problems in batches of about eight, each batch a commit that renders, lints and builds.
6. The whole booklet against the reference, then `errors/<vol>.md` finished.
7. `--dry-run` over the *next* year while this one is fresh — that is when the report is
   readable.

Per problem, fastest first, from the repository root:

```sh
uv run make render/naboj/phys/<vol>/problems/<pid>/sk/{problem,solution}.md
uv run python core/markdown-check.py render/naboj/phys/<vol>/problems/<pid>/sk/*.md
```

The lint must run on the **real render path**: `core/markdown-check.py` infers the module from
`path.parts[1]` and the problem id from `path.parts[5]`, so a hand-render into `/tmp` silently
disables the label rules.
