# Markdown dialect used by DGS

Source Markdown files (`problem.md`, `solution.md`, `answer.md`, `preamble.md`, ...)
are Pandoc-flavour Markdown with Jinja pre-processing on top and DGS-specific style
rules enforced by `core/mdcheck/`. This document lists the surface features you
actually need when writing problems, and the checker rules you must not trigger.

Jinja is covered separately in `jinja-templating.md`. LaTeX macros are in `latex-macros.md`.

## Math (inline and display)

Inline: `$…$`. Display: `$$ … $$` on its **own line each**, contents indented four spaces:

```
$$
    v_0 = \sqrt{2gh}.
$$ {#eq:falling-egg:v0}
```

- Label goes on the **same line as the closing `$$`**, separated by exactly one space.
- Label format: **the label prefix must always start with the problem id.**
  `solution.md` requires a sublabel: `{#eq:<problem-id>:<sublabel>}`.
  `problem.md` accepts a bare id (`{#eq:<problem-id>}`) or a sub-labelled form
  (`{#fig:<problem-id>:<sublabel>}`) — both pass the checker.
- Equations that need to be referred to across the solution get a sublabel;
  one-off equations in `problem.md` typically get no label at all.
- Cross-reference an equation: `[-@eq:<problem-id>:<sublabel>]` — the `-` produces an
  unadorned number (no "eq. " prefix).

Aligned block:

```
$${
    v_x &= v\cos\alpha, \\
    v_y &= v\sin\alpha.
}$$ {#eq:archery:vxvy}
```

Note the `${ … }$` variant is DGS's convention — the `{ … }` inside `$$` becomes an
`aligned` environment.

**Never** put `\begin{aligned}` / `\end{aligned}` on the same line as `$$`
(`mdcheck` DoubleDollars rule).

Punctuation inside math: the trailing character of a display equation is the natural
sentence punctuation (`.` `,` `;` `?` `!`). When using the Jinja math filters
(`| disp('.')`, `| align(',')`) the punctuation is appended for you.

## Figures

```
![Caption text](path/to/figure.svg){#fig:<problem-id>:<label> height=50mm}
```

- Caption is the alt text between `[]`.
- In `problem.md` the caption **must be empty** and the label may be omitted; in
  `solution.md` provide both caption and label (`{#fig:isic:isic-geometry ...}`).
- Attributes accepted (via pandoc's attribute syntax): `height=…mm`, `width=…mm`,
  `width=0.7\linewidth`, additional label anchors.
- Path is relative to the problem directory; DGS resolves it to `\activeDirectory/…`
  at the LaTeX stage.

## Cross-references

Handled by `pandoc-crossref` on the way to TeX:

- Equations: `[-@eq:archery:hd]` → `(1)` (or whatever number).
- Figures: `[-@fig:isic:isic-geometry]` → `1`.
- Tables: `{#tbl:…}` / `[-@tbl:…]`.

`mdcheck.check.Reference` verifies that the label prefix matches the problem id.

## siunitx in math

Numbers with units go through `siunitx`:

```
\qty{1.5}{\metre\per\second}                 # single value
\num{6.022e23}                                # dimensionless
\ang{45}                                       # degrees; NEVER use ^\circ
\qtylist{1;2;3}{\metre}                       # list, semicolons as separators
\qtyrange{5}{10}{\metre}                       # range
\numrange{1}{10}                               # dimensionless range
\numlist{1;2;3}
```

Forbidden inside `\qty{…}` / `\num{…}` / `\SIrange{…}`:

- `\cdot`, `\times`, `^` (use e-notation: `\num{5.1e7}` not `\num{5.1 \cdot 10^7}`).
  `mdcheck.SIExponents` flags this.
- Commas (`,`). Use `.` as decimal marker inside; siunitx localises for display.

Do **not** use raw `\SI`, `\SIrange`, `\SIlist` — replace with `\qty`, `\qtyrange`,
`\qtylist`. The linter (`osi`) enforces this.

Custom units declared in `core/latex/siunitx.tex`: `\gforce`, `\year`, `\inch`,
`\foot`, `\mile`, `\au`, `\parsec`, `\lightyear`, `\pound`, `\calorie`, `\erg`,
`\pixel`, `\eur`, `\atmosphere`, `\torr`, `\atomicmass`, `\molar`, `\dcelsius`
(delta degrees), `\solarmass`, `\earthmass`, `\solarluminosity`, `\horsepower`,
`\byte`, `\rpm`, `\jansky`, `\upmag`, `\mag`, `\permille`, `\ppm`, `\ppb`.

## Chemistry (chem module)

`\ce{...}` — reactions and formulas via `mhchem`.
`\chemfig{...}` — structural formulas.
`\Nuclide[A][Z]{sym}` — isotopes, e.g. `\Nuclide[99m]{Tc}`.

## Non-breaking spaces

DGS's convention for non-breaking space is `word\ text` — literal backslash-space.
This prevents ugly line breaks between short words and units / following text. Use
liberally after prepositions in Slavic languages (`v\ zime`, `s\ hmotnosťou`).

## Footnotes

```
… as computed above.^[Take the smaller root of the quadratic.]
```

Renders to `\footnote{…}` in TeX. Note: raw `\footnote` in the Markdown is banned
by `mdcheck` (`txf`).

## Lists and emphasis

Plain Markdown: `**bold**`, `_italic_`, `-` / `*` for bullets, `1.` for enumerated.
Do **not** write raw `\textit`, `\textbf`, `\textsf` — the linter forbids TeX font
styling (`txp`) and TeX headings (`txs`).

## Strikethrough

`~text~` renders to `\st{text}` (aliased to `\sout{}` via `ulem`).

## Fancy Unicode punctuation is banned

`mdcheck.uni` rejects: `“ ” ’ – — ~` in the source. Use plain ASCII (`"` `'` `-`)
or the LaTeX equivalents (`--` for en-dash, `---` for em-dash).

## Style checker (`core/mdcheck/check.py`) — the ones that bite

Line-length limit: 120 characters (`lln`). Break long lines at sentence or clause
boundaries.

Space rules:
- `eqs` — spaces around `=`, `\approx`, `\doteq`, `\geq`, `\leq`, `\gg`, `\ll`.
- `cdt` — spaces around `\cdot`.
- `pws` — spaces around `+`.
- `pas` — no space **after** `\left(` or **before** `\right)`.
- `dds` — `$$` alone on its own line (except with a label after it).

siunitx rules:
- `osi` — `\SI*` forbidden, use `\qty*`.
- `csi` — no comma inside `\qty{}`.
- `cnu` — no comma inside `\num{}`.
- `sie` — no `\cdot`/`\times`/`^` inside `\qty{}`/`\num{}`/`\ang{}`.
- `crc` — no `^\circ`, use `\ang{…}`.
- `vep` — no `\varepsilon` (patched to be `\epsilon` in `hacks.tex`).

TeX-macro discouraged:
- `sum` — replace `\sum` with `\Sum[lo][hi]{elt}`.
- `int` — replace `\int` with `\Int[a][b]{f}{x}`.
- `imp` — replace `\implies` with `\Implies`.
- `rar` — replace `\Rightarrow` with `\Implies`.
- `txp` — no `\textit`/`\textbf`/`\textsf` (use Markdown emphasis instead).
- `txs` — no `\section`/`\subsection` in Markdown.
- `txf` — no `\footnote` (use `^[…]`).
- `frb` — `\frac` must be followed by `{` (i.e. `\frac{a}{b}`, not `\frac ab`).
- `opa` — omit parentheses in simple function arguments: write `\sin\alpha`, not
  `\sin(\alpha)`.
- `lip` — no `\insertPicture` (use `![](…)` instead).

Typography:
- `tgc`, `thc` — no `\,` `\;` `\.` `\thinspace` (typographic corrections).
- `pun` — no punctuation inside `\text{}`.
- `tjs` — Slovak abbreviation spacing: write `t. j.` with a space, not `t.j.`.

Whitespace:
- `tab` — no tabs.
- `tws` — no trailing whitespace.
- `spb` — space before `\\` line-break in align.
- `lbw`, `rbw` — no whitespace immediately inside `{` `}`.

Language nitpicks (Slovak):
- `mzm` — `môžeme` (not `môžme`).
- `tht` — `tohto` (not `tohoto`).

Conflict markers: `cmk` — obviously fatal.

## Answer-specific rules

`answer.md`, `answer-also.md`, `answer-interval.md` all get one extra check:

- `fra` — must use `\dfrac`, not `\frac`. Answer cells are narrow and small; `\frac`
  produces cramped fractions there.

## Problem vs. solution label rules

`mdcheck.Reference` splits behaviour by filename:

- `problem.md`: label id prefix must match the problem name. Both bare
  (`{#eq:archery}`) and sub-labelled (`{#fig:archery:diagram}`) are accepted.
- `solution.md`: label **must** carry a sublabel matching
  `[a-zA-Z0-9_]+` — `{#eq:archery:hd}`.
- The `lfn` rule additionally guards against typo'd ids, and `lne` catches the
  narrow case of trailing junk between id and `}` in `problem.md`.

## Header/section commands

Do not write `#`, `##`, `\section`, `\subsection` in problems. The templates
(`modules/naboj/templates/blocks/*.jtex`) wrap each problem's contents in the
correct sectioning at assembly time.
