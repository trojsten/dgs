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
    [-P source/naboj/phys/29/problems/<pid>/preamble.md] \
    source/naboj/phys/29/problems/<pid>/sk/solution.md /tmp/out.md
```

Pass `-P` only when `preamble.md` exists — the renderer errors out if it is missing. Most
problems no longer have one: computed quantities belong in the `derived:` mapping in
`meta.yaml` (name → Jinja expression, evaluated in document order). `preamble.md` remains
only for computations needing real control flow.

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

**There is no fallback, deliberately.** Asking for a word the active language does not
define raises `MissingWordError`, naming the word, the language and the file to add it to.
`default.yaml` holds no `words:` for exactly this reason: `merge()` would make whatever it
held the fallback for every language, and a fallback for prose means a Slovak booklet
printing `therefore` — output that looks right until it is in print.

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
- Block equations belong in `meta.yaml` under `eq:`, referenced as
  `(§ eq.<name>|disp('.') §)`. The key becomes the label, so renaming a key
  renames `{#eq:<pid>:<key>}`.
