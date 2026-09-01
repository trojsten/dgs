# DGS

Náboj/seminar problem sources are rendered Markdown+Jinja → Markdown → TeX → PDF.
See `.claude/skills/naboj-authoring` for the authoring format.

Note `source/naboj/phys`, `source/naboj/chem` etc. are git submodules — problem
edits are committed there, not in the parent repo.

## Checking a problem

Render a single file (two passes; the second expands tags that came from `eq:`):

```
uv run python -m modules.naboj.builder.renderer sk \
    -C source/naboj/phys/29/problems/<pid>/meta.yaml \
    source/naboj/phys/29/problems/<pid>/sk/solution.md /tmp/out.md
```

Computed quantities belong in the `derived:` mapping in `meta.yaml` (name → Jinja
expression, evaluated in document order). **No problem has a `preamble.md` any more** —
the last nine, all in chem, moved into `derived:` and the file is gone from every volume,
so there is nothing left for the renderer's `-P` to point at. The flag and the prepending
behind it still exist in `core/builder/renderer.py` with no callers: neither `module.mk`
nor the editor mentions a preamble, and `chem/04/zinkový-plech` is the worked example of
what the migration looks like — five `@J set` lines became five `derived:` entries with
byte-identical output.

## The editor and the auditor

One Flask app, two pages. Run it from the repository root:

```
uv run python tools/editor/app.py [--port 5001]
```

- `/` — the editor: pick a problem, edit its sources and `meta.yaml`, render, compile,
  lint, and read the PDF beside them. Tab indents rather than moving focus — four spaces
  in the sources, two in `meta.yaml`, to the next stop; Shift+Tab outdents; Escape leaves
  the textarea, since Tab no longer does. A selection is never replaced, only indented.
- `/audit` — every volume in one table, then one volume in detail: an author
  leaderboard, tag distribution, files by language, and a verdict per problem for
  translations, equation de-duplication, pictures and `values:` extraction.

It must run from the root, and it `chdir`s there itself: several `core` modules open
their data by a repository-relative path, so `core/i18n` fails to import from anywhere
else. Port 5000 is the default but is often taken.

Both pages learn what a module contains from `modules/<module>/editor.yaml` — where the
units live, what files they hold, and which level (`scope:`) the audit aggregates at. A
fourth module needs a descriptor and no code.

What files a unit may hold comes from `module.mk`'s two rule families —
`NABOJ_TRANSLATABLE` inside `<language>/`, `NABOJ_NONTRANSLATABLE` beside the unit — by
way of the descriptor's `targets`/`translated`, which mirror them. `core/tests/test_audit.py`
fails if the mirror stops matching, so adding a file to module.mk cannot silently cost it a
column. The audit narrows that vocabulary to what a volume actually has, and gives each
remaining file a column of its own, grouped under its language.

**The audit covers `naboj` only**, by `audit: true` in its descriptor. The checks and the
four verdicts are Náboj's conventions — a language directory per problem, `values:` and
`eq:` in a meta, a volume `problems:` list — and seminar and scholar are built differently
enough that measuring them against these would report the difference as a defect. The
editor still edits all three. If either ever wants auditing it wants its own checks, not
the flag flipped.

The audit checks live in `core/audit/`, not in the app, because they are the durable
part: `checks.py` for the source-only ones, `status.py` for the four progress verdicts,
`build.py` for the slow ones.

The `values` verdict covers both directions: whether the numbers a statement *gives* are
named in `values:`, and whether the number a problem *produces* is computed. An answer
file holding a typed number is `answer-literal` — the answer belongs in `derived:` as
`result` and prints as `(§ result §)`, so that changing an input changes the answer.
`24/diesel` is the worked example.

Problems are listed in the volume meta's `problems:` order, because that list *is* the
running order and is what `ContextVolume` iterates. A problem missing from it is never
built; one listed without a directory gets `\protectedInput`'s red `Missing file` box in
the page, which is the intended behaviour — a hole in a booklet should be loud — but the
stale entry is still worth catching in the sources rather than in a PDF. Both directions
are checked (`unit-unlisted`, `listed-missing`). The page can sort alphabetically instead,
and keeps showing the competition number when it does. A pass over the whole repository is a fifth of a second, so
nothing is cached — except the build checks, which shell out to make and land in
`build/.audit/` with a fingerprint of the sources.

Adding a check means one function and two tests: one that it fires, one that it stays
quiet on a case that looks like it and is not. That second half is not optional. Every
one of those quiet cases in `core/tests/test_audit.py` is a false positive that a
hand-written version of the same sweep actually produced.

## Code layout

- `core/builder/jinja.py` — the two Jinja environments and the whole filter /
  global table. `MarkdownJinjaRenderer` is what `.md` sources see; the pint
  registry (including the `eur`/`€` currency unit) is set up at module level.
- `core/builder/context/quantities/` — `PhysicsQuantity`, `PhysicsConstant`
  (`constant.py`), `QuantityRange`, `QuantityList`, `QuantityProduct`,
  `MathObject` (`math.py`). All immutable except the symbol.
- `core/filters/` — thin Jinja-facing wrappers (`latex.py`, `numbers.py`,
  `hacks.py`). Most just delegate to a `PhysicsQuantity` method.
- `core/data/constants.yaml` — physical constants; the header comment documents
  the schema. `core/latex/*.tex` — the DGS class, macros, `siunitx` units.
- `modules/naboj/` — Náboj-specific renderer, templates (`*.jtex`), `module.mk`.

## Tests

`uv run pytest` (config in `pytest.ini`, tests in `core/tests/`). The suite is
the fast way to check anything in `core/` — it covers quantities, formatting,
filters, the Jinja environments and `MathObject` in detail. New filters or
quantity behaviour are expected to come with tests in the matching
`core/tests/test_*.py`.

## Pandoc

`core/builder/convertor.py` calls pandoc with `--from markdown+smart --to <fmt>
--pdf-engine xelatex --columns=200 --wrap=preserve --filter pandoc-crossref`.
`--wrap=preserve` plus the wide `--columns` mean the rendered Markdown's line
breaks survive into the TeX, so don't reflow rendered output to "fix" long lines.

## Style checker

`core/markdown-check.py <files>`. It infers the module from the *path*
(`path.parts[1]`) and the problem id from `path.parts[5]`, so it only works on
paths shaped `<root>/naboj/<comp>/<vol>/problems/<pid>/<lang>/<file>.md`.

Run it on **rendered** output, not source. On source it reports false positives:
`(§ eq.x|disp(',') §)` trips the "comma not followed by whitespace" rule. Labels
and most other rules are still meaningful on source.

Known checker gap: `format_general` emits Python's `e+NN`, and the "spaces around
`+`" rule flags it (`\qty{1.737e+06}{...}`). Not an authoring error — ignore.

## Translated words inside maths

A word that appears inside maths has to change with the language, and writing it out per
language means a separate copy of the equation per language — which is how the copies
drift apart. Two tiers, because the vocabulary splits cleanly:

- **Recurring words** live in `core/i18n/<lang>.yaml` under `words:` and are reached as
  `(§ i18n.words['and'] §)`. `and` and `or` cannot be written `i18n.words.and` — they are
  Jinja keywords, hence the subscript form.
- **A word belonging to one problem** goes in its `meta.yaml` under `words:`, term →
  language → text, one language per line, and is reached as `(§ words.air §)`. Of the 190 words
  found inside `\text{}` across phys, 167 appear in exactly one problem, so this is the
  common case.

A word is reached as `(§ i18n.andw §)` — the `w` because `and` is a Jinja keyword and
`i18n.and` will not parse. Only the keywords take it; `(§ i18n.therefore §)` is spelled as
written. `(§ i18n.words['and'] §)` still works and is the older spelling. `|q` and `|qq` wrap
a word in `\QText` / `\QQText`, so the whole thing is `(§ i18n.andw|qq §)`.

**There is no silent fallback, deliberately.** `default.yaml` holds no `words:`: `merge()`
would make whatever it held the fallback for every language, and a fallback for prose means a
Slovak booklet printing `therefore` — output that looks right until it is in print.

A word the language has not got is **boxed, not guessed**: the renderer emits
`\errorMessage{and?pl}`, which `core/latex/utilities.tex` sets as a red `\colorbox`, and
carries on. That is `\protectedInput`'s call for a missing file, for the same reason — one
absent word should not cost you the other 39 problems, and a translator wants the whole
booklet with the holes marked.

**The box is not the safety net.** Volume 19 printed `Missing file …onion…!` on page 42 in
every language for years while `make` stayed green, and the output already carries some 1500
of these boxes, so one more does not stand out. The net is two things: every miss is collected
and reported once at the end of the render, and `core/audit`'s `word-missing` check reads them
off the sources. Fix the word; do not ship the box.

Resolution is lazy, so a language that never asks for a word does not need it —
`21/troll-science` writes the equation with translated subscripts in four of its six
languages and differently in the other two.

The point is that `eq:` then holds the equation once. `21/troll-science` is the worked
example: `v_{\text{dopad}}`, `v_{\text{impact}}` and `v_{\text{becsapódás}}` became one
equation with three `words:` entries.

Notation that does **not** need this, because it is language-neutral already: water is
`\ce{H2O}`, the Earth is `\Earth` (`core/latex/symbols.tex` defines it as `\oplus`), and a
word subscript is always `\text{}` — `E_{kin}` is wrong, `E_{\text{kin}}` is right.

## Thin spaces, and why `\,` is banned

German abbreviations take a thin, non-breaking space between their parts -- `d. h.`
for *das heißt*, likewise `z. B.` and `u. a.` A full word space is too wide and a
line break between the halves is wrong. Write it as **`\thinspace`**:

    d.\thinspace h. um $\ang{45}$ gegenüber ...

`\,` looks like the obvious spelling and **does not work**. A backslash before
punctuation is a Markdown escape, so `d.\,h.` reaches the TeX as `d.,h.` -- a
literal comma inside the word, silently. The `tgc` rule flags `\,`, `\;` and `\.`
for exactly this reason and says what to use instead. `\thinspace` survives pandoc
verbatim because it is a control word, and LaTeX defines it as `\,` outright
(`latex.ltx`: `\let\thinspace\,`), so the typeset result is identical.

U+202F NARROW NO-BREAK SPACE also works -- pandoc turns it into `\,` -- and two
German solutions used it before `\thinspace` was allowed. Avoid it: it is
invisible in a diff, and Python's `str.isspace()` is true for it, so a whitespace
pass will flatten it to a plain space and quietly widen the gap. That happened
once already.

Do not use U+202F for a preposition either. That is `\ `, a normal non-breaking
space -- `v\ istej`, not a thin one. Nine chemistry problems had 57 of these from
a word processor; they are gone.

## Trailing whitespace — two kinds of it mean something

Strip trailing whitespace freely **except** in two cases, both of which a sweep has
already broken once:

- **A space after an odd run of backslashes is escaped.** That is the `\ `
  non-breaking space above, and thirteen `answer.md` files end a line with one.
  Strip the space and the bare `\` left behind is a Markdown hard line break, which
  pushes the figure below onto its own line -- `~` becomes `\hfill\break` in the
  TeX. An *even* run is escaped backslashes and the space after it is ordinary.
- **Two or more spaces before a line with content force a line break.**
  `chem/02/hviezdoslavov-kubín` is a poem and needs them between its verses,
  `chem/04/zase-nmr` hangs NMR data under each list item, and `FKS/39/1/2/06` holds
  a three-line author byline inside one italic span. The same spaces before a
  *blank* line are inert -- a break at the end of a paragraph does nothing.

A line that is *entirely* whitespace is never either of these, since a break needs
content before it. Empty it -- but check what it renders to first: volume 24's
Farsi statements each ended with a lone U+2003 EM SPACE, which pandoc set as its own
paragraph, so removing them changed the page rather than merely tidying it.

`core/audit/checks.py`'s `trailing_whitespace_is_meaningful` is the one place this
rule lives; the `encoding` check calls it, and a sweep should too.

## Symlinks — check before any bulk edit

**84 files under `source/` are symlinks, and `Path.write_text` follows them.**
A script that rewrites files per language will hit the same real file once per
link, and a second edit applied at offsets computed from the original text
shreds it.

    source/naboj/phys/27   78   cs/solution.md -> ../sk/solution.md, es -> ../en
    source/naboj/phys/26    4   truth-or-dare-elmag, four languages
    source/naboj/phys/00    2
    source/scholar          3   a shared picture

They are deliberate: a translation nobody has written yet mirrors its master
rather than keeping a stale copy, which is how `28/turntable` came to hold
physics that `sk` had already corrected. `NabojValidator` agrees, typing these
entries `FileOrLink`.

So in any script that edits sources:

- resolve first and write each real file once — keep a `set` of
  `path.resolve()` and skip a path already written;
- never assume "one file per language": 41 Czech and 43 Spanish solutions are
  not files;
- do not "fix" a mirrored translation by editing it, or the edit lands on `sk`
  or `en`.

This has bitten once and nearly twice. Hoisting equations in volume 27 corrupted
88 files exactly this way; volume 26 escaped only because its four links sit in
`truth-or-dare-elmag`, which has no equations to hoist. The renderer was
perfectly happy both times — it was caught by diffing pandoc's output before
and after. Reading through a symlink is safe; writing is not.

## Editing problem text

- Problem and solution prose is authored deliberately. Fix mechanical/style
  violations; do not reword, shorten, or drop words to satisfy a checker.
- The 120-char limit applies to the **source** line. Lines that only exceed it
  *after* substitution are fine and should be left alone.
- Long `eq:` entries wrap as YAML `|` block scalars — that is the idiom for
  keeping meta.yaml under the limit.
- **A vulgar fraction with a Unicode glyph is a named macro.** `core/latex/math.tex`
  defines nine — `\OneHalf`, `\OneThird`, `\TwoThirds`, `\OneQuarter`,
  `\ThreeQuarters`, `\OneEighth`, `\ThreeEighths`, `\FiveEighths`,
  `\SevenEighths` — and they are the whole set because MinionPro has no glyph for
  fifths, sixths, sevenths, ninths or tenths. **A missing glyph is not a compile
  error**: xelatex writes `Missing character:` to the log and sets nothing, so a
  `\TwoFifths` would silently vanish off the page. Anything the font cannot set
  stays `\nicefrac`, which builds its fraction from digits. `\nicefrac` also stays
  wherever a side is not a digit — `\nicefrac{r}{2}`, `\nicefrac{1}{\varkappa}`.
- **A display block and its terminal punctuation must agree about the paragraph.**
  Ending in a full stop ends the sentence, so a blank line follows and a new
  paragraph starts — unless the file ends there. Ending in a comma, a semicolon or
  nothing does not, so the prose carries straight on with no blank line between.
  The audit's `display-paragraph` reports the disagreement; it deliberately does
  not say which half is wrong, because a full stop with no break may be a missing
  blank line *or* a full stop that wanted to be a comma, and only the sentence
  says which. Three things exempt it: end of file, a next line Markdown needs a
  blank before anyway (list, figure, heading, another display), and a block
  indented inside a list item, where the next bullet is the break.
- Block equations belong in `meta.yaml` under `eq:`, referenced as
  `(§ eq.<name>|disp('.') §)`. The key becomes the label, so renaming a key
  renames `{#eq:<pid>:<key>}`.
- **The delimiters are the filter's job, not the fragment's.** `|disp` and `|align`
  make a display block, `|inl` makes `$…$`, and a *bare* `(§ eq.x §)` is the raw
  LaTeX with nothing around it — which is what lets one equation be spliced into
  another (`x = (§ eq.res §)` inside a bigger `eq:` entry). Never write
  `$(§ eq.x §)$` by hand; that is `|inl`, spelled longer. The default is raw
  because wrapping a bare fragment is one filter away, while unwrapping a
  pre-wrapped one is not possible in a template at all. Both mistakes fail the
  build loudly — bare in prose gives `! Missing $ inserted.`, and a `$` nested in
  a `$$` block gives `! Display math should end with $$.` — so neither is silent.
