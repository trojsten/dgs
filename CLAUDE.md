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
