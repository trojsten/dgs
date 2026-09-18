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
range. `29/folding-bath` is the worked example, and `29/drenched` is the one to read for why:
its solution names the air's density only as `\rho_a` and never prints a figure for it, so
nothing anchors the derivation to the table and the competitor's 955 ml is simply the right
number to show.

**Unless the solution quotes the constants, in which case it must compute with the ones it
quotes.** That is the real invariant, and printing `result_approx` is only the usual way of
satisfying it. `29/bolognese` states ρ = 1000, c = 4180 and l = 2260 in its prose, all
`constants.yaml` values, and so computes 334 kJ and 4.506 h from them and prints **`result`**;
the interval still reaches the sheet's arithmetic, so the competitor who read 2300 off the
sheet is still accepted. `00/horsing-around` and `24/crane` are the same shape, printing
`const.gforce` and `const.g` respectively. The failure this rule exists to prevent is a
solution that shows one set of constants and computes with the other — which is what
`bolognese` used to do, printing 2260 while computing with 2300.

So the check is not "does it print `result_approx`" but "does every number shown come from one
chain". A quick sweep for the mismatch: any problem defining both, whose displayed material
names no `const.` value, should print `result_approx` throughout.

Nothing needs padding because `QuantityRange.__format__` floors the minimum and ceils the
maximum at whatever precision is printed, so the printed band always contains the computed
one. **`widen` is gone — the method, the `|w` and `|widen` filters, and their tests.** It was
the workaround from when both ends rounded to nearest, and it hid the defect rather than
fixing it: `29/bouncy-v` spanned `[3.67749, 3.75]`, printed `3.7 – 3.8`, and turned away the
solver who used the exact `g`. Its last user was `27/electroballoon`, whose `|w(0.02)` stood
in for three real chains — the air's density from the table or the sheet, and hydrogen's
density read off a table rather than derived — which are now computed and spanned outright,
1170 to 1188 EUR against the 1147 to 1195 an arbitrary 2 % gave.

**When the band needs to be coarser than the last place it prints, that is `|snap(q)`.** The
grid `__format__` rounds outward onto is read off the printed string, so it stops at a whole
unit: `.0f` is the coarsest a format spec offers. `snap` chooses the grid instead.
`08/same-parallel` is the example — five printed figures for an answer good to four, so a
solver taking the 6378 km their school teaches wrote 11570 and the band ended at 11569.
`|snap(10)` prints 11550 – 11570. It moves each end to the next grid point and **no further**,
which is what makes it not `widen`: it is idempotent, and a range already on its grid does not
move.

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

## Reusable text: `blocks:`

A meta's four content keys each do something to what they hold, and until recently there was
nowhere to put text that should simply come back as written:

- `values:` — a given quantity. A bare string does pass through verbatim, but the name then
  claims the text is a number the statement gives.
- `derived:` — evaluated as a **Jinja expression**, in document order. Anything with two
  statements in it fails as `TemplateSyntaxError: chunk after expression`.
- `eq:` — wrapped in a `MathObject` and printed with an `{#eq:<pid>:<key>}` label attached.
- `blocks:` — **verbatim, namespaced**, reached as `(§ blocks.setup §)`.

The case it exists for is a gnuplot preamble. `FKS/42/1/1/03` plots three curves from one set of
axes, so its `normal.gp`, `abnormal-first.gp` and `abnormal-second.gp` each open with
`(§ blocks.setup §)` and add a single `plot` line. Two details matter when writing one:

- **`|`, never `>`.** A folded scalar collapses newlines into spaces, and gnuplot wants one
  directive per line — folded, the whole preamble arrives as a single unreadable line.
- **Tags inside a block are expanded by the second pass**, which is what lets the preamble write
  `tcold = (§ tcold.mag §)` and stay in step with the `values:` above it.

It is namespaced rather than spread into the top-level namespace, for the reason `words` is: a
block shadows nothing, so it may be called anything — `blocks.g` and the constant `g` coexist,
and a test says so. `blocks` itself is in `RESERVED_NAMES`, so no `values:` entry may take the
name. Adding it there was checked against every meta under `source/` first; reserving `w` once
broke eight problems, which is why that check is not optional.

## A code listing: `include()`

A solution that walks through a program shows the program, and the program is a real file —
`module.mk` copies every `source/seminar/<round>/<problem>/*.py` into `output/` for the reader to
download. So the listing must *be* that file, not a second copy of it that goes stale. Write the
fence and include it:

    ```python
    (§ include('vetranie.py') §)
    ```

The path is relative to the file the tag is written in, so it names the `.py` sitting beside the
`solution.md`. Inside a list item, chain Jinja's own `indent` exactly as an equation does:
`(§ include('x.py')|indent(4) §)`. Like `blocks:`, the text comes back as written and the second
pass expands it, so an included file may itself carry tags; unlike `blocks:`, a missing file
raises rather than resolving to nothing, because an empty code block compiles perfectly and
prints nothing.

This used to be `pandoc-include`'s `!include <file>` directive. That filter was dropped for the
warnings it emitted and nothing replaced it, so `FKS/39/1/2/05`, `40/1/3/07` and `40/2/1/05`
printed the literal line `!include kaboom.py` where the code belonged — and could not have shown
it anyway, because `Shaded` and `Highlighting` were undefined and those rounds never compiled at
all. Doing it in the renderer rather than in a filter means the code arrives before pandoc reads
the document, so it is syntax-highlighted like any other fenced block.

Three things the TeX side had to learn, all of them in `core/latex/`:

- **`Verbatim` does not report an overfull line.** It sets each one in a box it never breaks and
  never complains about, so a listing wider than the page walks off the paper in silence —
  `kaboom.py`'s longest line is 107 characters against about 98 that fit at 12pt. `Highlighting`
  therefore takes `fontsize=\small` and, through `fvextra`, `breaklines`/`breakanywhere`: anything
  still too wide wraps with a visible hookrightarrow instead of disappearing.
- **The monospace font takes no `tex-text` mapping.** That mapping is what turns `"` into `”`,
  `'` into `’` and `--` into an en dash — right for prose, and fatal in code, since the printed
  program will not run. It happens inside the font, so neither the Markdown nor the TeX shows it.
  `\setmonofont` in `fonts.tex` passes an empty `Mapping` to opt out.
- **Pandoc's highlighting macros are ours to supply.** `core/latex/highlighting.tex` is pandoc's
  own default block taken verbatim, so an upgrade can be diffed against it.

And one trap that only matters now that a listing can be a real file: **a line beginning with `%`
is a comment and is deleted**, by `RegexReplacement(r'^%.*$', …)` in `convertor.py`'s `pre_regexes`.
That rule is blind to fences, so it eats the comments out of any language whose comment character
is `%` — MATLAB, Octave, Erlang, PostScript, TeX — and leaves a blank line in their place, with no
warning. Python and gnuplot comment with `#` and are unaffected, which is every listing in the
repository today.

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

> **`\text{}` against `\mathrm{}` is being reopened, and nothing has been changed yet.** The rule
> above, and `subscript-unwrapped`'s message in `core/audit/checks.py`, both say `\text{}`
> outright. The revision is that **`\mathrm{}` is the right wrapper for a *symbol*, and `\text{}`
> stays for a *word*** — which is a real distinction and not a mechanical one, since deciding
> which a given subscript is takes judgement per site. Deliberately deferred until the whole
> ancient archive has landed, so the pass is done once over the finished corpus rather than twice.
>
> The scale, so nobody starts it by accident: **1975 `\text{}` in phys** (762 of them subscripts,
> 4 superscripts) against 20 `\mathrm{}`; 1532 against 58 in seminar; 237 against 0 in chem; 537
> against 1 in scholar. Until it is settled, keep writing `\text{}` — a mixed corpus is worse than
> a consistent one that is about to change, and the check enforces `\text{}` today.

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
- **A `magnitude:` in scientific notation must be written `1.0e+15`.** YAML 1.1 wants both a
  decimal point *and* a sign before it will read an exponent as a number, so `1e15`, `1e+15`
  and `1.0e15` all parse as bare **strings**. Nothing complains at that point — the schema
  accepts `Or(str, float, int, PhysicsConstant)` for a value, because a bare string is the
  documented way to pass LaTeX through verbatim — so the first sign of trouble is `derived:`
  reporting `unsupported operand type(s) for /: 'str' and 'float'`, a long way from the cause.
  `27/kamiokande`'s neutrino flux is the worked example.
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
- **`|arr` is for a display where more than one column has to line up**; `|align` is for a chain
  aligned on a single relation, and is right for 297 of the repository's 373 such blocks. `align`
  pairs its columns `rl rl rl`, so a block with two alignment points -- chemistry's
  quantity/formula/value chains, a system whose operators align -- comes out with the second
  relation ragged and the values not lining up at all. `arr` takes a column spec and must; an
  array has no sensible default:

      (§ eq.sys|arr('rcrcrcl') §)        (§ eq.MCaO|arrd('rclcl') §)

  It does three things for you, all of them `array` defects that would otherwise be the author's
  to remember. Every column is put in **display style**, because `array` sets its cells in text
  style and a `\frac` inside one would otherwise come out at script size -- that is what
  `\RequirePackage{array}` in `wrt.tex` is for. The terminal punctuation lands **inside the final
  cell**: after `\end{array}` a stop floats at the array's vertical centre, beside the middle row.
  And every row separator gets **`\jot`** of glue, because `array` zeroes `\baselineskip` and
  `\lineskip` and spaces its rows by a strut alone -- two rows of display-style fractions
  otherwise touch, which is what `20/star-triangle` did, one row's denominator sitting on the next
  row's numerator. `aligned` avoids that with `\openup\jot`; array ignores `\openup`, because it
  zeroes the very lengths `\openup` raises, so the glue has to ride on the separator. `\jot` by
  name rather than a length of the filter's own, because it is the document's setting for exactly
  this gap: `dgs.cls` puts it at 10pt, against plain LaTeX's 3pt, so anything tuned by eye in a
  scratch `article` would be wrong in a booklet.

  **What decides a conversion is how many relations a row carries.** `aligned` sets columns
  right, left, right, left … and pairs them, one `rl` pair per equation. So it is right for a
  chain with a single relation, and right for a *grid* of independent equations -- `22/seychelles`
  writes six coordinates as `T_1 &= … & T_2 &= … & T_3 &= …`, three perfect pairs -- and it is
  wrong for a **chain of two or more relations in one row**, whichever way that chain is spelled.
  `A &= B &= C` leaves `= C` in a right-aligned column, so the second relation is ragged.
  `A &=& B &=& C` looks like it fixes that and does not: `B` is now the *right* half of a pair,
  so it is pushed to the right edge of its column and a gap opens between the first `=` and the
  expression it introduces, as wide as the longest row needs. That was true of all 24 chemistry
  chains. The one spelling that does work is an empty right half, `A &= B &&= C &&= D`, which is
  what `chem/03/sírovka` uses.

  A scan for rows with two or more `&` found 74 blocks; a bit under half were worth moving, and
  the rest were grids, single chains, or a `&&=` already doing the right thing. `27/highway` and
  `20/star-triangle` are the worked examples.

  A **literal** `\begin{array}` -- the monolingual trees, where hoisting into `eq:` buys nothing --
  gets none of that automatically. Use the `L`, `C` and `R` column types from `core/latex/math.tex`
  for display style and write `\\[\jot]` on the separators yourself: `chem/03/veronikin-roztok`
  and `FKS/34/2/3/06` are the examples. Note that pandoc wraps display maths containing `\\` in an
  `aligned` of its own -- which is what the `$${ … }$$` idiom relies on -- but leaves a block
  alone once it opens with an explicit environment.
- **A block scalar takes its indentation from its first line.** If that line is deeper than the
  rows below it -- which is what lining up empty leading columns does -- YAML ends the block at the
  first shallower row and reports `expected <block end>` several lines later. Write `|2` rather
  than `|`: the indicator is relative to the parent node, so for an `eq:` entry it means the usual
  four spaces. `27/highway` carries one.
- **An equation inside a list item needs `|indent(4)`.** `disp` and `align` close at
  column 0 whatever indent the tag sits at, so a bare `(§ eq.x|disp('.') §)` inside a
  bullet puts its `$$ {#eq:…}` flush left and breaks out of the list. Jinja's own
  `indent` filter chains on and fixes it — its defaults are exactly right, `first=False`
  because the tag's own indent already covers the opening `$$`, and `blank=False` so no
  trailing whitespace is invented:

      -   … so the total resistance is
          (§ eq.r1|disp('.')|indent(4) §)

  `28/tetristor` is the worked example, and was the reason this was found: its three
  equations sat in bullets and so had been written out in all five solution files rather
  than hoisted. Nothing in the repository had ever indented an equation before, which is
  why the gap went unnoticed; `core/tests/test_jinja.py` now pins both halves.
