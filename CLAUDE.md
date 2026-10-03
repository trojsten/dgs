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
nothing is cached — except the two checks that cannot be answered by reading files, which land in
`build/.audit/` with a fingerprint of the sources: the build checks, which shell out to make, and
the macro sweep.

`macro-undefined` is the odd one out and worth knowing about. Whether `\Diff` exists is not a
question about the sources: `math.tex` names 191 macros, `dgs.cls` loads 146 packages that shadow
and complete each other, and the answers surprise in both directions — `\Chi` comes from mathspec,
`\diff` is defined by nothing although `\diff@` is. So `core/audit/macros.py` asks TeX, once, with
a probe that runs `\ifcsname` over every control word in the tree; `checks.macro_undefined` reads
the cached answer and places the findings. Run it from the `/audit` page's *Run macro sweep*
button or with `python -m core.audit.macros`; `--check` reads the cache instead and exits nonzero
if it is stale or was never run, which is the CI shape.

**No sweep, no findings** — the check reports nothing when the cache is absent, rather than
guessing. Two things it deliberately does not ask about: a meta is read *parsed*, because a
double-quoted YAML scalar has escapes of its own and `"Agata\tStefa\u0144ska"` otherwise offers
`\tStefa` as a control word; and chemfig's `\arrow` and `\schemestop` are named in `IGNORED`,
because chemfig defines them only inside a `\schemestart` group, which is the only place anyone
writes them.

It was worth having. `scholar/TA1` called `\diff` 222 times and `\OIInt` 22, `fks-naboj` called
`\EvalAt` and `\integrate`, `\fdiff`, `\pdiff`, `\Intx`, `\LogTen` and `\mustequal` were all
being written for macros that exist under another name — and none of it was visible, because
nothing builds those two modules.

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

> **A band whose two ends round to the same string should print that string once, and does not
> yet.** Outward rounding is right when the ends differ, and turns into noise when they do not:
> `06/earth-falls` has `result` 64.5663 and `result_approx` 64.5665 days, both of which *round*
> to 65 at `f0`, but the floor and the ceil pull them apart into `64 – 65` — a whole day claimed
> for two values agreeing to seven figures. The rule wanted is: **round each end to the requested
> precision first, and if the two strings are equal, emit the single value rather than a range.**
> That is not the same as `lower == upper` before formatting, which is the already-handled case of
> a constant that does not move at all, and it is the opposite direction from `|snap(q)`.
>
> Nothing is implemented. The workaround in the sources today is that such a problem simply has
> **no `answer-interval.md`** — 27 of them, spread across volumes 02 to 29, where the pair is
> computed in the meta and the band was left unwritten because it would have been a grid artefact.
> Once this lands, those files can be written and will print one value each, and the check that
> finds them is "does the interval's `|fN` render both ends to the same string".

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

## `=` or `\approx` is the quantity's to decide

`(§ x.eq §)` writes `=` only where the value is the true one **and** the figures it prints are
all of it. Otherwise it writes `\approx`. Two independent tests, because each catches what the
other cannot: `const.speed_sound` is 343 m/s, which prints back perfectly and is still not the
speed of sound, and only the declaration knows that; `sqrt(2)` is exact by every declaration on
its way there and prints as 1.41421, and only the arithmetic knows that.

`exact` defaults to **true**, because a number a statement *gives* is exact -- `s = 100 km` is
not approximately anything, and that is 196 of the sources' 217 `eq` sites. `constants.yaml` is
the exception: a value there is measured unless it says `exact: true`, which ten of the
sixty-five do. A `values:` entry may say `exact: false` for a given that is itself an
approximation.

It spreads through arithmetic as **contamination only** -- `a * b` is exact only if both are --
and never as a guarantee. An exact 100 km over an exact 3 h is 33.333..., which no decimal
string holds; `np.sin` builds its result without touching the operators at all. The round-trip
catches both, which is why the flag can afford to be optimistic about what it has not seen.

**Contamination reaches every operation, not just `_binop`.** It used not to: `__neg__`,
`__abs__`, `__rtruediv__` and the eleven numpy wrappers each built their result straight from
the constructor with no `exact=`, so it fell back to the default and the value came out exact
again -- negating a measured constant laundered it, and so did taking its cosine. They go
through `_unop` now. Nothing in 29 volumes moved when that was fixed, because the round-trip was
already overruling the laundered flag; it bites only where a result *does* print back exactly and
an operand was inexact, which is `cos(60°)` and which nothing happens to write.

### `digits` is presentation, and does not propagate

`digits` says how many figures to **print**. It is not an uncertainty, it is independent of
`exact`, and it does not travel through arithmetic. `speed_light` is exact by definition of the
metre *and* carries `digits: 1`, and both are right: the first is about the value, the second
about what the constants sheet shows.

It was made to propagate once, as a relative error -- `min` for products, absolute uncertainties
added for sums so that cancellation cost what it should. The arithmetic was right and the premise
was not. `gforce` is `digits: 1` because the table prints `10 m/s²`, so inheriting it claims a
precision nobody measured: `22/tea` computes 24.6 mm through `const.g.approx` and the booklet's
`25 mm` came out as `20`. A test pins that case.

So `digits` travels only where the quantity does -- `to`, `alias`, `simplify`, `approximate`, and
a sign -- and a result takes `None`, which `printed_digits` renders at `DEFAULT_DIGITS`. The one
thing rounding drives is **`\approx` instead of `=`**, which `approximate` expresses by clearing
`exact`. `alias()` takes no precision: digits are declared or they are absent.

### A symbol is declared on the quantity, not written beside it

`$\rho = (§ rho §)$` states that this symbol names that quantity, which is a fact about the
quantity. Put it there -- `symbol:` on a `values:` entry, `.alias('\\rho')` on a `derived:` one
(four backslashes in a double-quoted YAML scalar; `constants.yaml` already carries one for every
constant) -- and write one tag:

    $(§ rho.eq §)$              a value printed in full; `eq` picks `=` or `\approx`
    $(§ result|af(3) §)$        a value printed rounded: same figures, and `\approx` for it

**Which one is a question about the value, not about the source.** A given declared as exactly
2 g prints `2` at `|f0` and `2` in full, so nothing was rounded and `=` stands; `|af` there would
assert an approximation nobody made. Render both and compare.

`\doteq` is hand-written only, for an explicit rounding. No filter emits it, and the 24 sites
that used it in this shape now say `\approx`.

Five shapes look like this family and are not. The entry is **also a display** (`29/bolognese`
writes the same `eq:` key inline and through `|disp`, and removing it would take the display and
its `{#eq:}` label); the left-hand side is a **derivation** rather than a symbol
(`29/hot-shower`'s `\frac{(§ C2 §) - (§ C1 §)}{(§ T2 §) - (§ T1 §)}`, `28/egging`'s `H - h`); the
tag is **not a quantity** (`27/highway`'s `(§ peterInC.mag §)`, and `.mag` is a float); the
expression has **no name** to hang a symbol on (`(§ (h / 2)|f0 §)`); or the `derived:` expression
**spans several lines**, which cannot take an alias by line substitution.

The round-trip allows a thousand ulps. `29/coil-kirchhoff` solves a 3×3 system for a current
that is exactly 0.1 A and stores it six ulps out, so an equality test would call it rounded; the
two populations are nine orders of magnitude apart, so the threshold is not a tuned number.

Turning this on moved 25 sites in the whole repository, every one of them a measured constant --
`R_⊕`, `c_s`, water's heat capacity and latent heat, the Moon's radius. No `values:` entry
moved. Where the prose already says *približne*, the sentence now says it twice: `28/cave-explorers`
and `29/order-mass` read "approximately $c_s \approx 343$", and the word is now the redundant half.

`(§ x.apx §)` says `\approx` outright and at `digits:` figures rather than `%g`'s six; `|af`,
`|ag`, `|ae` take an explicit precision and, like `|ef`, consult nothing.

## When the booklet is wrong: `%# HISTORICAL:`

The ancient volumes survive only as their own PDFs, so the booklet is the source -- and
sometimes the booklet is wrong. Where its printed answer does not follow from its own
equations, the source carries a `%# HISTORICAL:` comment on the line it is on, saying what the
booklet prints and what the physics gives. `%` at the start of a line is deleted before the
page, so the note is for whoever reads the source, and `errors/NN.md` repeats it per volume.

Keep the two apart. A **decode loss** -- a square root floated off its line, a minus sign
gone, a fraction flattened into three rows -- is the extraction's fault and is simply repaired.
A **historical error** is the booklet's own, and is marked rather than silently corrected,
because the archive is a record of what was set in 2005 as much as it is a problem set.

Ten are marked so far. Two are still open, both because settling them needs a drawing nobody
has redrawn: `02/hilltop-gun`, whose statement says the gun fires horizontally while its
trajectory is a launch at alpha, and `09/two-weights`, whose own two equations give
l = (V_1 - V_2) rho g/(2k) against the /k it prints.

## Code layout

Two things `ls` will not tell you: the pint registry, including the `eur`/`€`
currency unit, is set up at module level in `core/builder/jinja.py`, which also
holds the whole filter / global table; and everything in
`core/builder/context/quantities/` is immutable except the symbol.

## What an author may type: `docs/filters.md`

Every filter, global, quantity attribute and `meta.yaml` key, with a worked example of each —
**182 filters and 32 globals** on the Markdown environment alone, of which only 57 names appear
anywhere in `source/`, because until now the only way to find one was to read `jinja.py`.

It is **generated** from the table in `core/builder/reference.py` by
`python -m core.builder.reference`, and `--check` exits nonzero when the file on disk is stale,
which is the CI shape `core/audit/macros.py` already uses. Do not edit it by hand.

The table is what it is — rather than a scrape of the docstrings — because the docstrings are
written for whoever maintains the code (`num`'s explains why it is idempotent) and ten filter
roots have none at all. An author needs "what do I type and what comes out", which is a different
text about the same function.

Three tests hold it to the code, and the point is that **drift fails the suite rather than
shipping**: the table's names must equal the registered names *in both directions*, so a filter
added without an entry goes red; every example is **rendered and compared** with the output
printed beside it; and `docs/filters.md` must match the generator. Adding a filter now means
adding its entry, and the example is executable, so it cannot be wrong for long.

**The two environments are disjoint**, which nothing said before: `MarkdownJinjaRenderer` serves
`.md` (and `.svg`/`.tikz` through `PictureJinjaRenderer`) and `StaticRenderer` serves `.jtex`.
`|disp` is written 4760 times and exists only in the first; `|upnth` is written 11 times and
exists only in the second. Either mistake is found by a failed build and by nothing else.

The editor serves the same table at `/api/reference` and shows it on hover, so the reference is
where the typing is.

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

## A meta's content keys are actually validated now

`values:`, `derived:`, `eq:`, `blocks:` and `words:` are checked against
`StandaloneContext._schema`, and until recently **none of them was**. The keys were written
`dict[ValidIdentifier, str]`, and enschema reads a subscripted generic as a *callable* — it
validates by calling it — so the whole check was "can this be passed to `dict()`". Neither the
key pattern nor the value type was looked at, for any of the five.

What that let through, each failing much later and somewhere else: a `derived:` entry holding a
number rather than an expression; an `eq:` key that is not an identifier; a `words:` term with a
bare string where its languages belong; and a `values:` entry with a misspelt `magnitude`, which
surfaced as a bare `KeyError: 'magnitude'` out of a constructor with nothing in it to say which
entry of which file was wrong.

They are written `{K: V}` now, which does validate, and a `values:` entry's own keys are spelled
out in `VALUE_ENTRY` — exactly the keywords the constructor takes: `magnitude` (required, and
`Or(int, float)`), `unit`, `symbol`, `digits`, `exact`, `si_extra`, `force_f`, `aliases`. Three
details worth knowing:

- **The mapping form goes last in the `Or`.** That is the alternative whose error gets reported,
  so a misspelt key fails as `Missing key: 'magnitude'` instead of `should be instance of
  'PhysicsConstant'`, which names the one form nobody wrote.
- **`magnitude` may not be a string**, which is what catches the `1e15` trap above at the key
  that caused it. The *entry* may still be a bare string — that is the documented way to pass
  LaTeX through — and a bare number is a dimensionless given written in one line.
- **`unit:` with nothing after it is dimensionless** and stays legal; that is how a ratio or a
  coefficient of friction is written.

Every `meta.yaml` under `source/` — all 2524 of them, 961 with content keys — was validated
against the new schema before it landed, and none failed. That check is not optional, for the
reason reserving `w` once broke eight problems.

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

## A picture is a template too

A `.tikz` or an `.svg` goes `source/ → render/ → build/`, the way a `.gp` always has, so a drawing
can print the number its `meta.yaml` computes instead of one typed in by hand. Same context, same
filters, same two passes. The `meta.yaml` **beside** the picture is the context -- there is no
search upwards, and a picture with no meta next to it fails rather than rendering against nothing.

It also means a picture no longer needs to live in a translation directory, because it can ask for
`(§ words.x §)` itself. `johan-august/sk/puzzle.tikz` was the only one in the repository that did
and has been moved up beside its meta; the Makefile's `pathlang` keeps the case and it should stay
empty.

**The block and comment tags move, because the defaults are the formats' own punctuation.**

| | Markdown, `.jtex`, `.gp` | `.tikz`, `.svg` |
|---|---|---|
| variable | `(§ x §)` | `(§ x §)` — unchanged |
| block | `(@ for … @)` | `(@§ for … §@)` |
| comment | `(# … #)` | `(#§ … §#)` |

`§` hugs the content in all three, and the character outside it says which tag it is. It has to be
this way round: `(§@` reads better and does not work, because Jinja matches the variable tag first
and leaves the `@` behind as *unexpected char*.

The two collisions are not hypothetical and not spellable-around:

- **`(#` is how SVG refers to anything it defines** — `url(#linearGradient42)`, `url(#Arrow1Mend)`,
  and the same for every clip path, mask and filter. **11081 of them across 2006 files**, 792 of
  those files in a module that builds. Jinja opens a comment on the `(#`, finds no `#)`, and the
  render dies on *Missing end of comment tag*.
- **`(@` is chemfig's arrow between named nodes** — `\arrow(@c2--c4){0}[-90]`, in two live
  chemistry pictures.

`.gp` is deliberately left in the Markdown dialect: gnuplot comments with `#` but never writes
`(#` or `(@`, so it has nothing to dodge, and the gnuplot templates that already carry tags would
have to be rewritten for nothing. `core/builder/renderer.py`'s `PICTURE_SUFFIXES` is the whole
rule, and `renderer_for` is tested in both directions.

**What an SVG can hold is narrower than what a TikZ can.** TikZ is LaTeX, so `(§ v.eq §)` typesets
properly. SVG text is set by `rsvg-convert` with system fonts, so the same tag prints the literal
string `v = \qty{10}{\metre\per\second}`. Nothing enforces it; the backslashes on the page are the
signal.

**`|txt` is the filter for that case** — a quantity written out, unit and all, with no TeX in it:

| | emits | for |
|---|---|---|
| `(§ v §)` | `\qty{3}{\metre\per\second}` | Markdown, `.tikz`, `eq:` |
| `(§ v\|txt §)` | `3 m/s` | `.svg`, a `.gp` axis label |
| `(§ v\|txt2 §)` | `3.00 m/s` | the `txt0`–`txt9` family, as `f0`–`f9` |
| `(§ const.gravity\|txtg §)` | `6.6743×10⁻¹¹ m³/kg/s²` | `g` notation, for anything `txt` would write as `0.0000000000…` |

The unit comes from **pint's own `~P` spec**, not a table of ours: short symbols, Unicode
superscripts for powers, `/` for division, `⋅` for multiplication. A table here would have to
carry every unit the sources use and would drift from the registry the values are built in. The
*magnitude* is ours, through the same `format_float` the `|f` family uses, so `|txt` and `|f`
agree about how many figures a value has where pint would print `3.0`. An exponent is superscripted
too, because `6.674e-11 m³⋅kg⁻¹` reads as two notations bolted together.

A bare degree closes up — `45°`, not `45 °` — mirroring `__format__`'s `\ang`; a rate of degrees
does not, so `30 deg/s`. `°C` keeps its space, as SI wants. `core/filters/plain.py` is the whole
of it.

A range, a list and a product print the way the booklet prints them, with the separators read off
`core/latex/siunitx.tex` rather than chosen: `75 cm – 77 cm`, `1 m, 2 m, 3 m`,
`3 cm × 4 cm × 5 cm` — en dash with spaces, comma and space, and units repeating, which is what
`range-units` and `list-units` are both set to.

**A range rounds to nearest here and outward in `__format__`, and that is the one place the two
disagree.** Outward rounding exists for `answer-interval.md`, which is the set of answers a marker
accepts — rounding its ends to nearest shrinks that set and turns away correct work, which is the
`29/bouncy-v` defect. Nothing `|txt` prints is an answer: a range in a drawing labels a span, and
moving its ends outward would claim a width nobody measured. Both behaviours are asserted in
`core/tests/test_filters.py`, so neither can be "fixed" into the other by accident.

Two things `|txt` inherits rather than fixes. pint normalises denominators, so water's heat
capacity is `4180 J/K/kg` — the same parked question as the siunitx side. And a unit the
arithmetic produced is the unit you get: `omega * R` is `3 m⋅rad/s`, so write `.to('m/s')`, which
is what `29/curveball`'s own `eq:` entries already do.

**Only reach for it where there is no TeX.** In Markdown, in a `.tikz`, in an `eq:`, `siunitx` is
better at this than a string can be — it sets the thin space, keeps number and unit on one line,
and matches the rest of the booklet.

Three more things about SVG specifically:

- **It does not reflow.** Text is absolutely positioned, so a substitution wider than the
  placeholder overflows or collides with whatever is beside it. 452 texts in `phys` are
  `text-anchor: middle` or `end` and tolerate it; the rest do not. Size the placeholder for the
  widest value the tag can produce.
- **The editor is safe, and was checked rather than assumed.** Inkscape keeps the payload as plain
  UTF-8 inside a `<tspan>`, so a tag typed with the text tool survives a save and still renders;
  a round trip through Inkscape 1.4 was run on a real drawing. Of 2373 tspans in `phys` only 9 use
  per-character kerning, and even those keep the string whole. The tag is consumed before
  `rsvg-convert` ever runs, so `§` needs to exist only in your editing font.
- **Text converted to paths loses the tag silently** — the one failure here with no symptom at all.

Nothing in the repository carried a tag when this landed, so the conversion had to be a no-op, and
was: of 1070 pictures rendered, 1059 came back byte-identical and 11 differed only by a stripped
trailing blank line, which is inert in both formats. The one picture that did not render,
`seminar/FKS/40/2/3/06/basket.svg`, failed on its problem's `meta.yaml` writing `value:` where the
schema wants `magnitude:` — that meta has never loaded and its `problem.md` fails the same way.

Sharing one drawing between two problems is a **symlink**, not an `include()`: the two can end up
in different volumes, and a path written into the text is the fragile half of that.

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
carries on to the end of the render. That is `\protectedInput`'s call for a missing file, for the
same reason — one absent word should not cost you the other 39 problems, and a translator wants
the whole booklet with the holes marked. **Then it fails**: the output is written, every gap is
reported at once, and the render exits nonzero, so `make` goes red. There is no fallback to
English anywhere and never was — eight `core/i18n/*.yaml` said there was, which was a note
describing code that did not exist.

**The box is not the safety net.** Volume 19 printed `Missing file …onion…!` on page 42 in
every language for years while `make` stayed green, and the output already carries some 1500
of these boxes, so one more does not stand out. The net is three things: every miss is collected,
reported once at the end of the render, and **the render then exits nonzero** — a warning is not a
failure, and that was the whole of the `onion` problem. `core/audit`'s `word-missing` check is the
fourth, and the only one that works without a build: it reads the sources, so it finds the gap in
every language at once before anyone renders anything. Fix the word; do not ship the box.

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

### Inline maths drifts too

Everything above is about display blocks, and inline spans have the same problem — worse, if
anything, because a span buried in a sentence is where nobody looks. **An inline span worth
hoisting is one that states a relation.** Concretely, `hoistable-inline` reports a span that,
after `strip_maths_whitespace`, is written out in two or more of a problem's real files and

- **carries a relation symbol** — `=`, `\doteq`, `\approx`, `\equiv`, `\propto`, or an
  inequality `<`, `>`, `\leq`, `\geq`, `\neq`, `\simeq`, `\cong`, `\sim`, `\ll`, `\gg`. An
  inequality is as much a statement as an equality: `$T_1 < T_H < T_2$` is a claim about the
  problem, `$\frac{r}{2}$` is a noun. Arrows are deliberately *not* in the set — `\to` is a limit
  (`\lim_{x \to 0}`) as often as it is a statement, and no regex tells the two apart;
- **and is at least 15 characters.** `$a = b$` reads better where it stands. The median span in
  the repository is 7 characters and 38 % are one to three, so the threshold is what separates a
  statement from a symbol, not a long span from a short one. `inline-long` at 90 is a different
  question — source readability of one span — and the two barely overlap.

Three things are excluded because each has its own home, and hoisting them would put the value in
the wrong one:

| excluded | belongs in | spelled |
|---|---|---|
| a bare `\qty{3.0}{\metre}` | `values:` | `(§ x §)`, `(§ x\|f2 §)` |
| `\alpha = \ang{45}` | `values:` | `(§ x.eq §)`, which picks `=` or `\approx` by `prints_exactly` |
| `F_{\text{miska}} = Mg` | `words:` | `(§ words.bowl §)` |

**`=` inside `[…]` is not a relation.** siunitx options are key–value — `\qty[per-mode = symbol]{…}`,
`\qty[parse-numbers = false]{…}` — and counting those would have added 22 false positives across
phys. The presence of such an option still means the span is doing something unusual and is worth
a glance; it is just not a statement.

**Spacing is the other half of the case.** `$a = b$` and `$a=b$` typeset identically, so nothing
ever forced the two to agree, and across phys 40 of 355 candidates are already written both ways —
`20/race` has `\frac{v_1}{v_2} = \frac{100}{80} = \frac{5}{4}` and the unspaced form of the same
line. One `eq:` entry settles the spelling once, which is a reason to hoist over and above keeping
the languages in step, and the check says so when it finds more than one spelling.

The hoist itself is mechanical: the fragment moves into `eq:` under a key, every copy becomes
`(§ eq.<key>|inl §)`, and **every language goes together**. Hoisting `sk` alone would leave `en`
holding a literal copy of something that now also lives in the meta — three spellings instead of
two, one of them indirect, which is worse than leaving it.

Volume 29 is the worked set: 53 fragments across 19 problems, `sk` and `en` together, and every
one of its files renders byte-identically before and after. That is the proof a
hoist wants — `|inl` emits exactly `$…$` around the fragment, so anything that moves the output is
a mistake. The one left alone is `29/order-mass`, whose `3 \cdot 16 = 48` is arithmetic done in a
sentence rather than a named relation; it carries `audit: {ignore: ['hoistable-inline']}` saying
so, the same way the `answer-literal` exemptions do.

The check is silent outside the multilingual trees. `chem`, `seminar/FKS`, `scholar/TA1` and
`fks-naboj` have one language and nothing to drift apart from.

## `$${ … }$$` is on its way out

It was DGS's own shorthand for an aligned display, and it works only because
`Convertor.pre_regexes` rewrites its two delimiters into `\begin{aligned}` and `\end{aligned}`
with a pair of per-line regexes. A custom extension no Markdown reader knows, for a form standard
LaTeX already has, rewritten by a line-oriented pass and therefore fragile in all the ways a
line-oriented pass is. The fewer of those the better.

`|align` no longer emits it: `MathObject` writes the longhand directly now, the same shape as
`arr` -- `\begin{aligned}` four spaces in, where `disp` puts its content, and the rows eight.

The 351 hand-written ones in 193 files stay for now and still build, because the rewrite regexes
stay until they are gone. What changed is that the tooling stopped recommending the shorthand:
the audit's `aligned-shorthand` reports it, and `mdcheck` no longer whitelists it. Both used to
say the opposite -- `aligned-longhand` reported `\begin{aligned}` and asked for `$${`, because
`MathObject` had a format spec for each and the same equation in two spellings read as two
equations. There is one spelling now. Convert a file when you touch it.

## The build inserts the non-breaking spaces, not you

A one-letter word must not end a line in Slovak, Czech, Polish, Russian or Ukrainian, and a
German abbreviation wants a thin space between its halves. Both used to be typed by hand --
`v\ zime`, `d.\thinspace h.` -- which is how the rule came to live only in authors' heads: it
was applied to some prepositions and not others, applied in English where the language does not
want it (`the\ velocities of\ both sound`, `18/submarine/en`), carried into `pl/` and `ru/` by
translators copying a Slovak file, and honoured in exactly two of the German solutions.

The rule belongs to the language being built, so **`core/filters/spacing.lua` does it**, and
authoring prose needs nothing. It is a pandoc Lua filter, listed after `quotes.lua` in
`Convertor.call_pandoc`, and the word lists live in `core/i18n/<lang>.yaml` under `typography:`:

    typography:
      singles: ['a', 'i', 'k', 'o', 's', 'u', 'v', 'z']
      nbsp_pairs: ['t. j.', 't. z.']
      thin_pairs: []                  # German's `d. h.`, `z. B.`, `u. a.`

`default.yaml` holds none of it, for the reason it holds no `words:` -- `merge()` would make one
language's list the fallback for every language, and English inheriting Slovak's prepositions is
the failure this is meant to end. Both cases of a single are derived in Python, so list a letter
once. A language that declares nothing gets nothing.

**It is in the AST, and that is the whole argument.** Pandoc has already decided what is prose:
`Math`, `Code`, `RawInline`, `RawBlock`, image and link targets and every attribute are separate
node types, so a rule written over `Str` and `Space` cannot reach them. Nothing has to be
re-detected, and nothing can be re-detected wrongly -- which a regex bank in `preprocess` would
have to do for `$…$`, `\qty{}`, fenced code, pipe tables, URLs and `![](path)`, one line at a
time. It also matches `SoftBreak`, not only `Space`: with `--wrap=preserve` the authored line
break survives into the TeX, where a newline is an ordinary breakable space, so a preposition
at the end of an authored line would otherwise still end a typeset line.

What it emits is Unicode -- U+00A0 and U+202F -- which pandoc's writers turn into `~` and `\,`
for LaTeX and into the characters themselves for HTML. One filter, both formats.

**Writing `\ ` by hand is still allowed and still correct**; it is the override for a case the
language rules miss, not the routine. Pandoc reads it as U+00A0 inside the `Str`, so there is no
`Space` left for the filter to touch and it cannot be doubled.

### What the sweep left behind, and why

`phys` has been swept: 3 115 of its 3 929 hand-written `\ ` are gone, decided one at a time by
the build itself -- remove the escape, convert both versions, keep the removal only when the TeX
is byte-identical. **814 stay, and they are not leftovers.** Almost all of them glue a word to
something the filter does not look at, because the filter's rule is about the token on the *left*
being a one-letter word:

- **497 `word\ $maths$`** -- `rýchlosťou\ $v$`, `pri dĺžke\ $L$`. A noun and the symbol it names.
- **33 the other way round** -- `aspoň $k$\ metrov`, `body $A$\ a\ $B$`.
- **23 `word\ \macro`** and **12 `\macro\ word`** -- `$R_x = 0\ \Omega$`, `\frac{c}{c-v}\ f`.
- **25 around numbers** -- `v bode\ 3`, `5\ dvojíc`, `medzi stavmi 1\ a\ 4`.
- **11 before a Jinja tag** -- `kolečko se\ (§ big §) zuby`.
- **183 word to word**, which is where the languages differ: `ve`×18 and `ze`×6 in Czech,
  `a`×24 and `the`×8 in English, `egy`×7 in Hungarian, `so`/`do`/`na` in Slovak.

Leave them. A rule for "a noun and its symbol" would need to know which noun, which is a job for
an author and not for a filter.

`errors/` holds 13 more, in prose *about* the sources, and those stay too.

The metas held 343, but **340 of them were never markup**: PyYAML wraps a long double-quoted
scalar by ending the line with `\` and opening the next with `\ `, the `\ ` restoring the space
the fold would otherwise eat. In a venue's team list that `\ ` *is* the space between two names,
so stripping it merges them, silently. Those scalars are now unwrapped onto single lines -- 631
lines joined across 31 files -- and the escapes are gone with them. Two shapes had to be undone
and in this order: a break at a space (`…Galuska-Tomsits\` + `\ Ádin`) rejoins with a space, a
break inside a word (`…ker\xFC\` + `let"`) with nothing. Every file was re-parsed and asserted
equal to what it parsed to before; that assert is the only reason to trust the transform.

Line length does not matter in these files -- they are a registration export, not prose.

What is left in the metas is 3 real `\ `, each a `number\ unit` inside an `eq:`.

### A hyphen that repeats itself

Five of the twelve languages repeat the hyphen when a word breaks at one: `anti-inflamatório`
sets as `anti-` / `-inflamatório`, never `anti-` / `inflamatório`. **Which five was swept against
each language's own authority, not assumed**, because the answer is not guessable — the two
Slavic languages that repeat and the two that do not sit side by side.

| | repeats? | source |
|---|---|---|
| Czech | **yes** | ÚJČ, *Internetová jazyková příručka* §164, after ČSN 01 6910: *"Pokud se spojovník objeví na konci řádku a nenaznačuje neúplné slovo, opakuje se na začátku řádku dalšího"* — `česko-` / `-polské` |
| Slovak | **yes** | STN 01 6910: *"Ak je spojovník na konci riadka, musí sa zopakovať aj na začiatku nasledujúceho riadka"*, and it lists the omission among the commonest errors |
| Polish | **yes** | PWN, rule [196] — `czarno-` / `-białe`, `warmińsko-` / `-mazurskie` |
| Portuguese | **yes** | Acordo Ortográfico 1990, **Base XX, item 6** — `ex-` / `-alferes`, `vice-` / `-almirante` |
| Spanish | **yes, with an exception** | RAE, *Ortografía* 2010 — `léxico-` / `-semántico`, **but not** before a proper noun: `Ruiz-` / `Giménez` |
| German | no | Duden: the Bindestrich *"gilt bei der Worttrennung am Zeilenende gleichzeitig auch als Trennungsstrich"* |
| French | no | OQLF: *"on ne le répète donc pas au début de la ligne suivante"* |
| Hungarian | no | AkH. 12th ed. §238: *"a kötőjelet csak a sor végén tesszük ki. Ennek a sor elején való megismétlése csak szakmunkákban szokás"* |
| Russian | no | Milchin: *"при переносе слов с дефисом последний обычно не повторяется"*; some sources advise not breaking at a hyphen at all |
| Ukrainian | no | the Правопис's технічні правила переносу do not state it |
| English | no | no style guide prescribes it |
| Farsi | n/a | hyphens are rare and compounds are joined with ZWNJ, not hyphens |

**The Spanish exception is the one that matters here**, and it is Spanish's alone: a capital
already shows the hyphen is not a division mark, so `Gay-Lussac`, `Navier-Stokes` and
`Gutenberg-Richter` must *not* repeat. Slovak is the opposite — STN gives `Rakúsko-Uhorsko` and
`Bratislava-Ružinov` as cases that do. `typography: repeat_hyphen_not_before_capital` carries it,
and only `es` sets it.

Portuguese needs the rule most often, because enclitic pronouns put a hyphen inside ordinary
verbs — `encontra-se`, `deu-lhe`, `colocou-o`.

**A hyphen joining a digit to a word must not break at all**, and that has to be said out loud
rather than left to omission. Czech typography forbids dividing `3-dílný` or `10-procentní` at
the spojovník, the Ukrainian Правопис forbids separating a grammatical ending from its digits
(`10-й`), and the Russian rules forbid it for `2-местный`, `Боинг-767` and multi-digit numbers.
Since the five repeating languages carry a lowered `exhyphenpenalty`, a hyphen merely *left
alone* would be freely breakable — so the filter emits `\nbhyphen` (an `\mbox{-}`, no
discretionary) whenever a digit sits on either side. Slovak has 70 of these in its sources,
`10-stupňovej` and `12-krát` among them.

**Russian is deliberately not in the table.** Its own rules *permit* the break — `сет-клин` and
`монотип-клавиатура` are their examples — they merely do not repeat the hyphen, so a blanket
`exhyphenpenalty: 10000` for Russian would forbid what the norm allows. What Russian forbids is
the digit case, which is the paragraph above and is not Russian-specific.

Authoring needs nothing: `core/filters/hyphens.lua` puts `\rephyphen` wherever a declaring
language has a hyphen between two letters, the same way `spacing.lua` handles the non-breaking
spaces and for the same reason — a hyphen in these sources is far more often *not* prose
(`northern-sun.svg`, `{#fig:drag-queen}`, `forbid-literal-units=false`, `$a-b$`) and pandoc has
already sorted those into node types a `Str` rule cannot reach. A language opts in with
`typography: repeat_hyphen: true`; one that declares nothing keeps the plain hyphen.

Unlike `spacing.lua` it is **LaTeX only**. That filter emits Unicode and serves both writers from
one rule; no Unicode character repeats a hyphen at a break — U+00AD SOFT HYPHEN inserts one but
does not repeat it — so HTML keeps the plain hyphen.

**Two things about the macro, both of which cost a rebuild to find.** It is
`\mbox{-}\discretionary{}{-}{}` in `core/latex/hacks.tex`, and neither half is arbitrary:

- The pre-break list is **empty**, with the hyphen written before the discretionary. TeX governs
  a discretionary break by `\exhyphenpenalty` when the pre-break list is empty and by
  `\hyphenpenalty` when it is not — so babel's own `\babelhyphen{repeat}`, which is
  `\discretionary{-}{-}{-}`, is governed by `\hyphenpenalty` and **does not break at all** here.
  Written this way the two penalties stay independent, and whatever `dgs.cls` does to ordinary
  hyphenation cannot switch this rule off.
- The hyphen is in an **`\mbox`**, because TeX inserts a breakpoint of its own after an explicit
  hyphen character, that one sits *before* the discretionary, and it costs the same
  `\exhyphenpenalty`. With both legal TeX takes the earlier and the hyphen is not repeated — a
  bug that shows up only on words short enough for the two breakpoints to compete, which is why
  `anti-inflamatório` looked right while `encontraram-se` did not. `\char`\-` does not help: it is
  still an explicit hyphen to the line breaker.

The rule is inert unless the language also lowers `latex: exhyphenpenalty`, which is the only
thing that decides whether the break may happen at all; the three carry 50, TeX's own default.
Lowering it from the ban changed nothing in volume 28 — all three booklets build with zero
hyphen-broken lines — so this buys a breakpoint for the lines that need one and costs nothing
elsewhere.

### Where the per-language lists come from

Each `typography:` block cites its source, because the lists are transcribed, not invented.

- **Czech** -- ČSN 01 6910 by way of the Institute of the Czech Language: `k, s, v, z`, `o, u`,
  `a, i`. The vocalised `ve, ze, ke, se` are **not** in the norm, however often they are typed.
- **Russian** -- Milchin §1.4.17.3 enumerates exactly `а, в, и, к, о, с, у`.
- **Ukrainian** -- the rule is stated ("особливо одно- та двобуквеними"), so unlike the two above
  it reaches two-letter prepositions. No source enumerates the words, so the two-letter half is
  the prepositions the sources actually write (`на до за із зі по об`); the conjunction `та` is
  left out on purpose, since gluing it would take a sixth of the Ukrainian text and nothing asks
  for it. This is also why `convertor.py` derives three cases and not two: a sentence opens with
  `Із`, not `ІЗ`, and for a one-letter word the two forms coincide, so the gap went unnoticed.
- **Hungarian has no such rule and declares no `singles:`.** The standard reference on Hungarian
  technical typography is explicit that it used to: *"Ma már eltörhető a sor az egybetűs szavak
  után (a, e, ó, ő, s) … A jóval korábban készült [forrás] nem engedi meg a sorvégi egybetűs
  szavakat."* The seven `egy\ ` in the Hungarian sources are an author's preference.
- `я` was in the Russian and Ukrainian lists and is a pronoun; no rule covers it, so it is gone.

### `\,` is still banned in the source

`\,` looks like the obvious spelling of a thin space and **does not work**. A backslash before
punctuation is a Markdown escape, so `d.\,h.` reaches the TeX as `d.,h.` -- a literal comma
inside the word, silently. The `tgc` rule flags `\,`, `\;` and `\.` for exactly this reason.
`\thinspace` is the escape hatch for a pair `thin_pairs:` does not know: it survives pandoc
verbatim because it is a control word, and LaTeX defines it as `\,` outright (`latex.ltx`:
`\let\thinspace\,`), so the typeset result is identical. Prefer adding the pair to the YAML.

U+202F NARROW NO-BREAK SPACE also works -- pandoc turns it into `\,` -- but never write one:
it is invisible in a diff, and Python's `str.isspace()` is true for it, so a whitespace pass
will flatten it to a plain space and quietly widen the gap. That happened once already. The
same goes for using one as a preposition's space; that was never thin in the first place. Nine
chemistry problems had 57 of these from a word processor; they are gone.

### What the filter does not reach

215 `.jtex` templates never pass through pandoc, and 29 of them contain a hand-written `\ `.
In TeX `\ ` is plain control space and **breakable** -- `~` is `\nobreakspace`
(`latex.ltx:6908-6911`) -- so `s\ úlohou` in `29/languages/sk/instructions-inner.jtex` does not
prevent the break it was written to prevent. Those want `~`, and nothing inserts it for them.

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
  and `1.0e15` all parse as bare **strings**. **The schema now rejects that**, naming the key —
  `magnitude` is `Or(int, float)`, and a string there is never anything but this mistake.
  `27/kamiokande`'s neutrino flux is the worked example. Until it did, nothing complained at
  that point and the first sign of trouble was `derived:` reporting `unsupported operand
  type(s) for /: 'str' and 'float'`, a long way from the cause.
- **Spell a unit the way pint spells it**, because `values:` and `derived:` render through pint
  and anything else blocks a hoist. Three pairs, all of them identical on the page -- a probe
  compiled against `dgs.cls` prints `150 kg` and `1000 kg/m3 5 m2` from either side -- so this is
  a source convention, not a typographic one:

  | write | not |
  |---|---|
  | `\kilo\gram` | `\kilogram`, and likewise any unit siunitx also offers as one macro |
  | `\metre\cubed`, `\metre\squared` | `\cubic\metre`, `\square\metre` |
  | `\metre` | `\meter` |

  The cost of getting it wrong is invisible until you try to hoist: a solution writing
  `\qty{1000}{\kilo\gram\per\cubic\metre}` cannot be pointed at the value holding that same
  number, because the rendered output moves and the byte-identity gate refuses it. `21/moonshine`
  is the worked example -- once respelled, its four languages' literal water density became
  `(§ const.density_water.approx §)`. `20/see-the-sun` had `\metre` in `sk` and `\meter` in `en`
  and `hu`, which is the same defect wearing a different hat.

  phys and chem are clean. The 35 in `seminar` and 32 in `fks-naboj` are not ours to touch.

> **Which way round a compound unit's denominators go is unresolved, and deliberately parked.**
> pint normalises `kJ/(kg·K)` to `kJ·K⁻¹·kg⁻¹`, so it prints **`kJ/(K kg)`** where an author
> writing the unit by hand prints `kJ/(kg K)`. Unlike `\kilogram` above this is *not* cosmetic:
> `per-mode` is set to a fraction, so the symbols genuinely swap places on the page.
>
> The cost today is two literals, and they are the same literal. `11/pudding` and
> `18/shower-heater` both write `\qty{4.2}{...}` and `\qty{4180}{...}` for water's heat capacity
> while `values.c` holds the same number, and in each it is the only number in the problem still
> written out twice -- everything else in both is hoisted. Any problem whose `values:` carries a
> compound unit with two denominators will hit the same wall.
>
> Settling it means choosing whether the booklet prints pint's order or the author's, and if the
> author's, giving the quantity a way to say so. Not urgent; do not silently reorder a printed
> unit to make a hoist go through.

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
- **A spaced connective is a macro, never its spelling.** `\Implies`, not
  `\quad\Rightarrow\quad`; `\Iff` and `\ImpliedBy` for the other two arrows, and `\LAnd`,
  `\LOr`, `\LXor`, `\LNand` for the logical ones. All seven are in `core/latex/math.tex`,
  where the comment above them explains why they are `\NewDocumentCommand` rather than
  `\DeclareMathOperator`: an operator *name* is set upright and given operator spacing, and
  both are wrong for a binary relation.

  The point of the macro is that the spacing is decided once. Written out, it drifts —
  `seminar` had 35 `\quad\Rightarrow\quad` against 26 `\qquad\Rightarrow\qquad`, the same
  connective at two widths, and nothing to say which was meant. They are all `\Implies` now.

  **A bare `\Rightarrow` is a different thing and stays.** Opening a row inside an `aligned`,
  `&\Rightarrow R_p &= \ldots`, the column is the spacing; `\Implies` there would add a `\quad`
  the alignment did not ask for. 21 of those in `seminar` were deliberately left.
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
- **An answer file holds the answer, not a sentence about it.** `answer.md` is what a marker
  compares against, so it is the value and nothing else: `\dfrac{k(k+2)}{2k+1}`, not
  `\dfrac{h_2}{h_1} = \dfrac{k(k+2)}{2k+1}`. The symbol on the left restates the question, which
  the marker already has in front of them, and it costs a line of the answer booklet per problem.

  **In the solution the opposite is usually true**: the final display is a step in a derivation
  and the left-hand side says what is being computed. Desirable there, not required, and never
  carried over into `answer.md`.

  Three things earn an `=`, and they have one thing in common -- the left side carries
  information the right side cannot:

  - **Several quantities at once.** `chem/.pool/trojroztok` answers
    `V_A = \qty{910}{\micro\litre}, V_B = …`, and without the names the three numbers are a
    puzzle of their own. Seven answers are of this shape.
  - **A ratio whose members are not named by the statement.** `04/energy-ratio` answers
    `E_k : E_p = 15 : 1`; a bare `15 : 1` says nothing about which way round it goes.
    `06/weighted-triangle` and `08/escape-match` are the other two. A ratio that *is* a complete
    value -- one number -- needs no label.
  - **The statement asks for that form**, for instance when it says to give the answer as an
    equation.

  An `=` between **two spellings of the same value** is not this and is always fine:
  `\qty{960}{\giga\joule} = \qty{9.6e11}{\joule}`, or the factored and expanded forms of one
  expression side by side. 152 answers do it, and it is often the kindest thing for a marker.

  > **278 answers in phys are still of the `symbol = value` shape, and nothing has been swept.**
  > The rule is written down first so that new problems follow it; the archive is a separate
  > pass, and an `answer-labelled` check would report 287 findings across the repository on the
  > day it was added. Worth doing, not worth doing by accident.

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
- **A problem statement never numbers its equations, and never labels them.** The number would
  be a cross-reference to something the contestant does not have in front of them during the
  competition, and a label nobody may point at is a number in the margin for nothing.

  This is **not** a filter you choose. `MathObject` takes a `labelled` flag and the renderer sets
  it from the file being rendered, against the module's own `equation_numbering` — a mapping
  stated in **both** directions, so that reading it tells you the whole taxonomy rather than only
  where it differs from a default:

  ```python
  # modules/naboj/builder/renderer.py
  equation_numbering = {
      'problem.md':          False,   'solution.md':        True,
      'problem-extra.md':    False,   'answer.md':          True,
                                      'answer-extra.md':    True,
                                      'answer-also.md':     True,
                                      'answer-interval.md': True,
  }
  ```

  **A file it does not mention keeps its numbers.** That default is the conservative one on
  purpose: a module that declares nothing is unaffected, and a file type added later is numbered
  until somebody decides otherwise rather than silently losing its labels. The answer files are
  listed although none carries a display today — they are part of the taxonomy, and
  `test_renderer` pins the keys to the two rule families in `module.mk`, so a file added to the
  module cannot inherit the default without someone noticing.

  **The mapping is the module's, not core's**, for the reason `editor.yaml` and the audit's
  `audit: true` are per module: another module's files mean different things. Seminar nests
  `problem.md` five levels deep and scholar also has `text.md`, a lecture, whose equations
  *should* be numbered. `core.builder.renderer.CLIInterface.equation_numbering` is empty.

  **Why not an explicit `label=` on `|disp`?** Because the call is not hoisted even when the
  equation is. There are 5264 call sites naming 2579 distinct equations, so more than half of all
  equations are written out once per language — `label=False` would be written six times for one
  equation and could be forgotten in one of them, giving an equation numbered in Slovak and not
  in English. That is the same one-language drift hoisting exists to prevent. And those argument
  lists already vary per language *legitimately*: 141 equations are called with different
  terminal punctuation in different languages, because the punctuation follows the sentence
  around the display, which is a translator's call. A `label=` would sit in exactly that argument
  list, varied by the same hand. (A per-entry flag in `meta.yaml` would be un-driftable but
  cannot express the case that matters: the same entry unlabelled in the statement and labelled
  in the solution.)

  It is also what lets **one `eq:` entry serve both halves of a problem**, which is the whole
  reason statements can be hoisted at all. `26/earthquakes` states the Gutenberg–Richter law and
  then opens its solution with it: the same `(§ eq.grl|disp(',') §)` stands in both files, the
  statement gets no label and the solution gets `{#eq:earthquakes:grl}`, so there is one copy of
  the equation and still exactly one label to reference. Before this, hoisting a statement
  equation that the solution also printed would have emitted the label twice.

  **Hoisting a statement matters more than hoisting a solution**, not less: the statement is what
  contestants read during the competition, and it must not drift. It had: `20/gases` wrote the
  rate law out in five languages and the Hungarian had lost its minus sign, so one booklet told
  its readers the amount of A *grows*. Four languages agreed and the fifth was wrong, and nothing
  reported it.

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
  `aligned` of its own -- which is what the deprecated `$${ … }$$` idiom relied on -- but leaves
  a block alone once it opens with an explicit environment.
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
