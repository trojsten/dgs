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
expression, evaluated in document order). **`preamble.md` is gone, mechanism and all** —
no source has one, and `JinjaConvertor` no longer takes a preamble, no longer has a
`prepare_template` step, and no longer accepts `-P`. The last nine files were all in chem
and every surviving line in them was a plain `@J set`, never the control flow the preamble
existed for, so `derived:` took the lot. `chem/04/zinkový-plech` is the worked example:
five `@J set` lines became five `derived:` entries with byte-identical output.

If you meet a `-P` in an old note or transcript, drop it — argparse now exits on it, which
is deliberate. A flag silently ignored would read as though it still worked.

## The audit's conventions

How to run the editor and the `/audit` page, and how a module declares itself to them,
is in `.claude/skills/dgs-editor`. What the checks *mean* is here, because it governs
editing problems rather than running the app.

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

## An answer interval is a span, not a tolerance

`answer-interval.md` is the set of answers a marker accepts, so it is **the span over every
admissible value of every constant, and nothing else**. No padding.

Admissible means two values per constant: the one in `core/data/constants.yaml`, and the one
the constants sheet prints — that constant's `digits:` applied, which is what `.approx`
returns. The competitor is holding the sheet, so both are legitimate arithmetic.

So `derived:` carries the pair, and the names are `result` and `result_approx`:

    derived:
      result:        "(k * L0**2 / (2 * m * const.g)).to('cm')"
      result_approx: "(k * L0**2 / (2 * m * const.g.approx)).to('cm')"

The solution and `answer.md` print **`result_approx`** — that is the number a competitor
computes, and the solution has to be followable with the sheet in front of them. The interval
is `(§ (result % result_approx)|fN §)`, smaller endpoint first, since `%` refuses a reversed
range. `29/folding-bath` and `29/bolognese` are the worked examples.

Nothing needs padding because `QuantityRange.__format__` floors the minimum and ceils the
maximum at whatever precision is printed, so the printed band always contains the computed
one. **`|widen` (`|w`) is not for this.** It was the workaround from when both ends rounded to
nearest, and it hid the defect rather than fixing it: `29/bouncy-v` spanned `[3.67749, 3.75]`,
printed `3.7 – 3.8`, and turned away the solver who used the exact `g`. **There is no `|w` or
`|widen` left anywhere in phys.** The filter is still defined — `widen` is a real operation on a
range and the tests cover it — but no answer interval should reach for it.

Name the pair this way round even where it reads oddly. `28/nevera` and `28/avocado` used to
call the sheet's value `result` and the real one `result_exact`, the inverse of here, and the
cost was not cosmetic: `%` refuses a reversed range, so the two problems ordered their operands
oppositely — `(result % result_exact)` in one, `(result_exact % result)` in the other — and both
were right. Whoever wrote the next one had to work out which name meant which before they could
write the interval at all.

Two things to check when writing one:

- **More than one constant that moves?** Then the extremes need not be the all-exact and
  all-sheet corners — evaluate them. Every interval in 29 is safe, but only for a reason:
  `bolognese`'s density cancels algebraically and its heat capacity does not move, leaving the
  latent heat alone; `folding-bath`'s density and `g` enter solely as the product `ρg`.
- **Does any constant move at all?** A `digits:` that reproduces the magnitude exactly does not
  — `refraction_water` is `1.3330` to four digits, so `29/speedy-reflection` spans on `g` alone.
  If *none* moves, the pair is a single point and the sheet prints `x – x`.

## Code layout

Two things `ls` will not tell you: the pint registry, including the `eur`/`€`
currency unit, is set up at module level in `core/builder/jinja.py`, which also
holds the whole filter / global table; and everything in
`core/builder/context/quantities/` is immutable except the symbol.

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

## Deduplicating across translations — and when not to

Hoisting an equation into `eq:` removes the per-language latitude a translator otherwise
has, deliberately: the physics is the same in every language, and copies drift. But it is
not worth any cost. **A troll answer, an argument that only prose carries, an answer made of
words — these are worth leaving alone**, and the metas that do so say why in place.

Volume 28 is the worked set. All 22 of its drifted equations turned out to be localised
notation rather than disagreement, and the same three questions decided every one:

- **Does a subscript abbreviate a prose word, or is it declared?** `28/elevator` wrote `m_v`
  for an elevator in English, because Slovak's *výťah* had leaked everywhere — an undeclared
  abbreviation, so it follows the language, and is upright. `28/refills` says outright
  "denote the small bottle by the subscripts $s$" — a letter its own sentence defines is
  already right for its reader whatever it abbreviates, so those stay as declared, and stay
  italic, being indices rather than words.
- **Is it a term the statement defines?** Then it follows the reader's *statement*, not the
  prose it stands in. `28/john-doe` invents three units named per language, so Polish reads
  an English solution using `łyk` — the unit its own statement introduced. That is the
  opposite of the subscript rule above, and for a reason: the statement is what tells the
  reader what the word means.
- **Do the derivations actually agree?** `28/egging`'s Ukrainian reaches the answer another
  way and its `h` is the others' `H - h`. Bending one route onto the other to satisfy a
  check would be rewriting physics, so the four that agree share an `eq:` entry and Ukrainian
  keeps its own. Nothing is then duplicated, and the check goes quiet because there is
  genuinely nothing left to hoist.

The same applies to answers. `answer-literal` wants the result computed, and `28/central-lamp`
answers 100 % whatever its refractive index is, `28/gravity-sudoku` answers 0 because a
solved sudoku's rows all sum to 45, and `28/balance-me` answers which two of nine planets
are left over. None is the output of a calculation; all three carry
`audit: {ignore: ['answer-literal']}` with the reason, and `value_status` honours that.

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
  non-breaking space above. Strip the space and the bare `\` left behind is a
  Markdown hard line break -- `~` becomes `\hfill\break` in the TeX. An *even* run
  is escaped backslashes and the space after it is ordinary. Eleven `answer.md`
  files used to open with one of these; they do not any more (see *A picture as the
  whole answer* below), and the only file left ending a line with one is
  `chem/02/oganesón`, whose six are the spacing between orbitals inside a `$$` block.
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
- **How to spell a fraction — four tiers, in order.**
  1. **A Unicode vulgar glyph**, wherever the fraction is a standalone value, and
     above all in a mixed number: `33\OneThird`, `666\TwoThirds`. `core/latex/math.tex`
     defines nine — `\OneHalf`, `\OneThird`, `\TwoThirds`, `\OneQuarter`,
     `\ThreeQuarters`, `\OneEighth`, `\ThreeEighths`, `\FiveEighths`,
     `\SevenEighths` — and they are the whole set because MinionPro has no glyph for
     fifths, sixths, sevenths, ninths or tenths. **A missing glyph is not a compile
     error**: xelatex writes `Missing character:` to the log and sets nothing, so a
     `\TwoFifths` would silently vanish off the page.
  2. **`\dfrac`** in an answer file, where a full-height fraction is wanted — that is
     where 251 of the repository's 309 `\dfrac` uses already are.
  3. **`\nicefrac` only inside `^{}` and `_{}`**, where `\frac` would stack a
     full-size fraction at script size: `x^{\nicefrac{2}{5}}`,
     `\int_{-\nicefrac{\ell}{2}}`.
  4. **`\frac`** everywhere else, prose included, and for a coefficient inside a
     formula: `\frac{1}{2} m v^2` stays, and `\frac{r}{2}` inline is right.

  `\nicefrac` used to be tier 4's answer and is not any more. It stays *defined*
  regardless — `math.tex` takes it as one of `\Drv`'s fraction styles, so removing the
  macro would break the derivative notation.
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
- **A picture as the whole answer needs nothing around it.** Write the image on its
  own and stop -- no leading `\ `, no `\vspace`. Eleven answer files used to carry
  both, and the reason is worth knowing because the symptom comes back looking like
  a Markdown problem when it is a TeX one: the problem number is a `titlesec`
  `[runin]` subsection title, which needs a paragraph to sit in, and `\insertPicture`
  is vertical-mode material, so the title was deferred to the *next* paragraph and
  the number printed **under** its own picture. The escaped non-breaking space was
  there to open a paragraph for it; the negative `\vspace` -- `-8mm` to `-13mm`,
  tuned per drawing -- then cancelled the `\topsep` that `center` had added. Both
  halves were invisible to the author and went stale whenever a picture was resized.
  `\tightPictures` in `core/latex/utilities.tex` now does it in one place: inside an
  answer block only, `\insertPicture` opens the paragraph with `\leavevmode` and sets
  the drawing on the number's own line, raised so its top edge is level with it and
  centred between two `\hfill` in whatever width the number leaves. Nothing there is
  a tuned length, and the picture cannot collide with the number however wide it
  grows. Everywhere else -- a picture in a problem or a solution -- `\insertPicture`
  is unchanged and keeps its `center`.

  The same block/inline split decides the punctuation. `answer-extra`,
  `answer-interval` and `answer-also` are glued onto the answer with `\answerJoin`,
  which is a comma while the answer is running text and **nothing** once the answer
  has ended its own paragraph -- there is no line left for a comma to sit on, so it
  would open a new paragraph and print alone, which is what `21/pv-to-vt-2` did under
  its diagram. `\answerJoin` tests `\ifvmode` rather than inspecting the source, so it
  is right for a picture, a list, a display, and for an `answer.md` that exists but is
  empty (`28/john-doe`, `20/big-brother`, whose whole answer is the extra). Nothing to
  do when authoring either way: write the extra and the join sorts itself out.
- **The booklet's closing credits are one block.** The four author lists and the
  colophon under their rule are one credit, so `blocks/booklet/footer.jtex` wraps
  them in `footerBlock`, which collects them into a box -- a box cannot be broken --
  measures it, and takes a new page *before* laying down the fill if what is left of
  the page will not hold it. `21/sk` used to split it four names from the end, with
  `Obrázky` dangling on the foot of one page and the colophon stranded at the top of
  the next. A `\vfill` on its own cannot fix that in either direction: glue is a legal
  breakpoint, so TeX breaks *inside* the block, and glue is discarded both at a break
  and at the head of a fresh page, so the fill that was meant to seat the block at the
  foot evaporates -- hence the box, the explicit `\newpage`, and `\vspace*{\fill}`
  rather than `\vfill`. Adding a name costs nothing; a block taller than a page would
  overrun the margin and say so as an Overfull `\vbox`.
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
