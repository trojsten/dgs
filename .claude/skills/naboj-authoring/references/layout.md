# File layout of a Náboj volume

## Volume directory

```
source/naboj/<comp>/<vol>/
├── meta.yaml                              # volume-level metadata (see below)
├── languages/
│   └── <lang>/
│       ├── meta.yaml                      # per-language booklet contents flags
│       ├── intro.jtex                     # editor's letter (uses (* … *) tags)
│       ├── instructions-inner.jtex
│       └── evaluators.jtex
├── venues/
│   └── <venue-junior|senior>/
│       └── meta.yaml
└── problems/
    └── <problem-id>/
        ├── meta.yaml                      # per-problem metadata (see below)
        ├── answer.md                      # the answer expression (Jinja, non-translatable)
        ├── answer-also.md                 # (optional) accepted alternative
        ├── answer-interval.md             # (optional) accepted interval
        ├── <figure>.svg / .tikz / .png    # (optional) referenced by both problem and solution
        └── <lang>/
            ├── problem.md                 # the problem statement (Jinja + Markdown)
            ├── problem-extra.md           # (optional, rare) extra content appended after problem
            └── solution.md                # the worked solution
```

`<comp>` is `phys` or `chem`; `<vol>` is a two-digit numeric volume id.

## Volume `meta.yaml`

Fields observed in `source/naboj/phys/28/meta.yaml`:

```yaml
date:   2025-11-07
start:  '11:30'
problems: [gravity-sudoku, train-mirror, balance-me, ...]    # ordered!
workshop: 'chata Alexa, Oravská Lesná'
authors:
  problems: [ "Martin ‚Kvík‘ Baláž", ... ]
  pictures: [...]
  editors:  [...]
  head:     "Jaroslav Valovčan"
venues:
  ba:  { name: Bratislava,  head: "Katarína Nedeľková" }
  ke:  { name: Košice,      head: "Marián Kireš" }
  # ...
table: 8                                    # answer table columns
constants:                                  # constants that appear in the printed table
  generic:   [gforce, avogadro, universal_gas, boltzmann]
  astronomy: [speed_light, gravity, radius_earth, ...]
  elmag:     [permittivity, mass_electron, elementary_charge]
  misc:      [stefan_boltzmann, density_water, ...]
```

`problems:` fixes the **order** in which problems appear (numbering follows this list).
Every id listed must exist as `problems/<id>/`.

## Problem `meta.yaml`

Minimal (no computed values, hard-coded numbers in the Markdown):

```yaml
authors:
  idea: ['Kvík']          # whoever thought of the problem
  problem: []             # whoever wrote the statement
  solution: []            # whoever wrote up the solution
tags: ['kinematics']
```

`authors` is a mapping of those three roles, not a list of names — all three keys are
optional, so a problem records only what is known, and `authors: {}` is the honest form when
nobody wrote it down. A bare `author: 'Kvík'` appears in two chemistry problems and the
schema rejects it.

### `tags:`

At least one, every one from `VALID_TAGS` in `modules/naboj/builder/renderer.py`, which is
the whole vocabulary and carries a one-line gloss per tag. Grouped there by area: the physics
topics, then the chemistry ones, then a handful describing what *kind* of problem it is rather
than what it is about (`troll`, `silly`, `trick`, `puzzle`, `matching`, `ordering`,
`truth-or-dare`, `incorrect`).

Read the list before inventing a spelling. `valid_tag` is in the schema but never actually
runs — enschema does not check the elements of `list[And(str, valid_tag)]` — so a typo costs
nothing at build time and twelve pairs of near-synonyms drifted apart that way before being
merged. What does catch it is `core/audit`'s `tag-unknown`.

Tags are shared across competitions wherever the word already means the right thing:
chemistry problems use `gases` for the state equation, `nuclear` for decay, and
`calorimetry`, `mixing`, `buoyancy`, `geometry`, `math` and `units` as written.

With values (used as Jinja variables inside `problem.md`, `solution.md`, `answer.md`,
...):

```yaml
authors: ['Kvík']
tags: ['kinematics', 'oblique-throw']
values:
  v0:
    magnitude: 50
    unit: 'metre / second'          # pint syntax; see quantities-and-constants.md
    symbol: 'v_0'                    # TeX symbol used by |eq / .eq
  D:
    magnitude: 70
    unit: 'metre'
    symbol: 'd'
```

Dimensionless values: use `unit: ~` or `unit: '1'`.

Percentages: `unit: '%'`. Angles: `unit: 'degree'` or `'radian'`.

`siunitx` extras (rare, e.g. force `per-mode`):

```yaml
values:
  acc:
    magnitude: 2.6
    unit: "kilometre / hour / second"
    si_extra:
      per-mode: "repeated-symbol"
    symbol: a
```

A value can also be a bare string or number — no Quantity is constructed then.

`author:` (singular) is accepted in older volumes; new problems use `authors: [...]`.

### `eq:` — named math fragments (chem)

Alongside `values:`, `meta.yaml` can carry an `eq:` top-level dict. Each entry
becomes a `MathObject` addressable in Jinja as `eq.<name>`. Its content is a
LaTeX fragment that may itself contain `(§ … §)` tags — those are expanded on
the second render pass (see `jinja-templating.md` §Two-pass rendering).

Canonical example: `source/naboj/chem/04/problems/maliari/meta.yaml`.

```yaml
values:
  m: { magnitude: 140, unit: 'g' }
  w: { magnitude: 0.88, unit: '1' }
eq:
  m: |
    m(\ce{Zn}) =
    m(\text{kov}) \cdot w(\ce{Zn}) =
    (§ m|f0 §) \cdot (§ (w.to('1'))|f2 §) =
    (§ (m * w)|f1 §).
  Mr: |
    M_r(\ce{ZnSO4})
    &= A_r(\ce{Zn}) + A_r(\ce{S}) + 4 A_r(\ce{O}) \\
    &= (§ const.M_Zn §) + (§ const.M_S §) + 4 \cdot (§ const.M_O §) =
    (§ M_ZnSO4|f2 §).
```

Then in `solution.md`:

```
Hmotnosť rozpusteného zinku preto bude
(§ eq.m|disp §)

Molekulová hmotnosť síranu zinočnatého je
(§ eq.Mr|align §)
```

`|disp` produces `$$\n    …\n$$ {#eq:maliari:m}` and `|align` produces the
`aligned` variant (`&`-alignment supported). The label is generated
automatically as `{#eq:<problem-id>:<name>}` — do **not** add your own.

Constraints:
- The name must match `^[a-z][a-zA-Z0-9_]+$` and cannot be `eq` or `const`.
- Names are validated by `StandaloneContext._schema` in `renderer.py`.
- More common in `chem` than `phys`; useful when the same computation is
  displayed *and* re-used later as a labelled equation.

## `derived:` — computed quantities

Everything a problem computes from its `values:` and `const` belongs in the `derived:`
mapping in `meta.yaml`, as *name: expression*:

```yaml
derived:
  result:       'v0**2 / const.g.approx - sqrt((v0**4 / const.g.approx**2) - D**2)'
  result_exact: 'v0**2 / const.g - sqrt((v0**4 / const.g**2) - D**2)'
```

- Evaluated in document order, so an entry may use anything defined above it, plus every
  `value:`, `const.x`, and all the usual globals (`sqrt`, `pi`, `PQ`, …) and methods
  (`.to()`, `.alias()`, `.approx`).
- The results are ordinary context variables: `(§ result|f2 §)` in any of the problem's
  files, including inside `eq:` entries.
- Quote expressions with **double quotes outside, single quotes inside**, so nested Jinja
  strings read naturally: `"(x).to('km/h')"`, `"y.alias('a')"`.
- A backslash inside a double-quoted scalar must be escaped — write
  `"z.alias('f_{\\mathrm{max}}')"`. A single `\` is an unknown YAML escape and fails to
  parse, which is at least loud.
- A failing expression raises `DerivedQuantityError` naming the key, and an unknown name
  raises `MissingVariablesError` — neither silently yields an empty value.

Convention: compute a rounded-`const.g` variant (`.approx`) alongside an exact-`const.g`
variant so both `answer.md` (rounded target for competitors) and `solution.md` (exact
expression) get sensible values.

## `preamble.md` — gone

There is none left anywhere under `source/`. Every computation lives in `derived:`.

The last nine were all in chem: two were empty, and seven were plain sequences of
`@J set <name> = <expression>` — which is precisely what `derived:` evaluates, in the same
Jinja environment and in the same document order. So not one of them needed the control
flow the preamble existed for.

Do not create one: nothing would read it. `JinjaConvertor` takes no preamble, has no
`prepare_template` step, and `-P` is no longer a flag — argparse exits on it rather than
ignoring it, so an old command line fails instead of appearing to work.

## `answer.md` / `answer-also.md` / `answer-interval.md`

Single line (no trailing newline needed), typically referencing a `derived:` quantity:

```
(§ result|f0 §)
```

- `answer.md` — the canonical answer displayed on the answer sheet.
- `answer-also.md` — an alternative accepted answer, typeset after "also".
- `answer-interval.md` — an interval, typeset after "interval". Usually `(§ (a % b)|f2 §)`
  where `%` constructs a `QuantityRange`, or `(§ x|w(0.05)|f2 §)` for a ±5% tolerance.

All three are **non-translatable** (same file across languages). If wrapped in `$…$` they
render as inline math on the answer sheet.

The linter forbids `\frac` here — use `\dfrac` because answer cells are typeset small.

## Language directory (`<lang>/`)

- `problem.md` — problem statement in that language.
- `solution.md` — worked solution.
- `problem-extra.md` — rarely used, gets appended in the booklet after the problem.
- `answer-extra.md` — rarely used, gets appended after the answer.

Supported language codes (see `Makefile`): `sk en cs hu pl es de fr ru fa uk pt`.

## Figures

- `.svg` — rendered via `rsvg-convert` / `dvisvgm`.
- `.tikz` — inline TikZ, wrapped by the pipeline.
- `.png`, `.jpg` — embedded directly.

Figures live at the **problem level** (not per-language). Reference from Markdown:

```
![Caption text](my-figure.svg){#fig:<problem-id>:<label> height=50mm}
```

Different languages can have different captions but reference the same file. Height/width
via `height=50mm` / `width=0.7\linewidth` inside the attributes braces.
