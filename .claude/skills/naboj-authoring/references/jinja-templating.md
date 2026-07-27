# Jinja2 templating in DGS

DGS uses **two** Jinja environments with different delimiters. Get the file type
right and everything follows.

## Delimiters by file type

### Markdown files (`.md` under `source/`)

Custom delimiters chosen so as not to clash with Markdown / TeX syntax:

| Purpose                 | Delimiter        | Example                       |
| ----------------------- | ---------------- | ----------------------------- |
| Variable expression     | `(§ … §)`        | `(§ v0|f2 §)`                 |
| Block statement         | `(@ … @)`        | `(@ if fig @)…(@ endif @)`    |
| Comment                 | `(# … #)`        | `(# note: dead code #)`       |
| Line statement prefix   | `@J ` (with space)| `@J set result = v0 + v1`    |
| Line comment prefix     | `%#`             | `%# throwaway comment`        |

`trim_blocks=True`, `autoescape=False`. Missing variables are **collected and
raised together** as `MissingVariablesError` after render — you'll see them all at
once. Filters may still catch undefined via `|default(...)` without triggering the
error.

### Static TeX templates (`.jtex` under `modules/naboj/templates/` and `core/templates/`)

Different delimiters — variables use `(* … *)`:

| Purpose                 | Delimiter        | Example                       |
| ----------------------- | ---------------- | ----------------------------- |
| Variable expression     | `(* … *)`        | `(* problem.number *)`        |
| Block statement         | `(@ … @)`        | `(@ if target=='booklet' @)…` |
| Comment                 | `(# … #)`        |                               |
| Line statement prefix   | `@J `            |                               |

Everything else about the environments is identical.

## Rendering flow for `.md` files

`core/builder/renderer.py::JinjaConvertor.run` does **two passes**:

1. Prepend `preamble.md` (if any).
2. First render pass: expands values, equations, `@J set …`.
3. Second render pass: re-renders the intermediate so that any Jinja tags that
   appear **inside expanded content** (e.g. inside a MathObject) get expanded too.

This is why you can write things like `(§ result|f0 §)` in `answer.md` and have
`result` come from `preamble.md` — the preamble is prepended before the first pass.

The second pass matters most for `eq:` fragments: `(§ eq.foo|disp §)` expands
on pass 1 to a display equation whose body still contains raw `(§ … §)` tags
(the ones defined in the `eq:` YAML value); pass 2 evaluates those inner tags.
Without the second pass, `eq:` would be useless.

## Context available in Markdown Jinja

Provided by `core/builder/renderer.py::CLIInterface.build_context`:

- `id` — the problem id (from directory name).
- **Every key under `values:` in `meta.yaml`** becomes a variable in the local
  scope. If the value is a dict with `magnitude:` and `unit:`, it becomes a
  `PhysicsQuantity`; if a bare string/number, it's used as-is.
- **Every key under `eq:` in `meta.yaml`** becomes a `MathObject` accessible as
  `eq.<name>`. The `MathObject`'s `.id` is set to `<problem-id>:<name>` so
  `|disp` and `|align` emit a label automatically. See
  `source/naboj/chem/04/problems/maliari/` for the canonical example — the
  content of each `eq:` entry can itself contain `(§ … §)` tags, which get
  expanded on the **second** render pass (see below).
- `const` — the physics constants dict from `core/data/constants.yaml`. Access as
  `const.g`, `const.G`, `const.c`, `const.gforce`, ... aliases are also mapped.

## Filters (registered in `core/builder/jinja.py::MarkdownJinjaRenderer`)

Number formatting — precision-parameterised versions are pre-generated for 0–9
digits. Apply to `PhysicsQuantity`, `QuantityRange`, `QuantityList`,
`QuantityProduct`, or a raw number:

| Filter               | What it does                                              |
| -------------------- | --------------------------------------------------------- |
| `|f`, `|f0`, ..., `|f9` | Fixed-decimal formatting. `q|f2` → `\qty{50.00}{...}`  |
| `|g`, `|g0`, ..., `|g9` | General formatting (may use scientific). `q|g3`       |
| `|n`                 | Wrap raw value in `\num{…}` (no unit).                    |
| `|nf`, `|nf0..9`     | `\num{…}` with fixed precision.                           |
| `|ng`, `|ng0..9`     | `\num{…}` with general precision.                         |
| `|ef`, `|ef0..9`     | `symbol = \qty{…}` fixed. Uses `PhysicsQuantity.symbol`.  |
| `|eg`, `|eg0..9`     | Same, general precision.                                  |
| `|mag`               | Extract raw magnitude (pint magnitude, not a string).     |
| `|unit`              | Just the unit, formatted as `\unit{…}`.                   |
| `|sim`               | `.simplify()` — convert to base SI units.                 |
| `|w(value)`, `|widen(value)` | Construct a tolerance range: `x|w(0.05)` → ±5%.   |

For a `MathObject`:

| Filter        | What it does                                                     |
| ------------- | ---------------------------------------------------------------- |
| `|inline`     | Renders `$…$`. Write sentence punctuation **outside** the tag.  |
| `|disp`       | Renders `$$\n    …\n$$ {#eq:<id>}`.                              |
| `|disp('.')`  | Same with trailing punctuation inside the math.                  |
| `|align`      | `$${\n    …\n}$$ {#eq:<id>}` (aligned environment).              |
| `|align(',')` | Same with punctuation.                                           |

## Globals

Math functions available in Jinja expressions:

```
sin  cos  tan  asin  acos  atan  atan2
sqrt cbrt log log10 log2 exp pow
ceil floor
rad  deg                       # radians ↔ degrees
gamma beta                     # Γ and B(x,y) = Γ(x)Γ(y)/Γ(x+y)
pi   tau  euler                # constants
```

These accept both raw numbers and `PhysicsQuantity` values (pint routes through).

Constructors (short aliases in parentheses):

```
Q(magnitude, unit)             # ad-hoc PhysicsQuantity, e.g. Q(100, '%')
QuantityList(q1, q2, q3)       # (QL) combine several commensurate quantities into a list
QuantityProduct(q1, q2, q3)    # (QP) combine several commensurate quantities into a product (e.g. box dimensions)
QuantityRange(lo, hi)          # (QR) build a range directly; equivalent to `lo % hi`
```

`q1 % q2` and `q.widen(v)` remain the idiomatic ways to build a `QuantityRange` (see
quantities-and-constants.md); `QR(lo, hi)` is there for when the operands aren't
bare variables and `%` would need extra parens anyway.

## `@J set` — the everyday case

Used almost exclusively inside `preamble.md`:

```
@J set result       = v0**2 / const.g.approx - sqrt((v0**4 / const.g.approx**2) - D**2)
@J set result_exact = v0**2 / const.g       - sqrt((v0**4 / const.g**2)       - D**2)
```

The `@J` (line-statement prefix) form is preferred over `(@ set … @)` for
readability. Idiomatic pattern: compute a rounded-constant version for `answer.md`
and an exact-constant version for `solution.md`.

## Control flow (`.jtex` templates)

Standard Jinja `if / for` blocks with the DGS delimiters:

```
(@ for vid, venue in volume.venues.items() @)%
    (* venue.head *) ((* i18n[language.id].venues[vid] *))%
(@ endfor @)%
```

Whitespace control follows Jinja: `(@- … -@)` trims surrounding whitespace.

Path helpers available in static templates:

- `path_exists('some/path')` — check whether a file exists (used to conditionally
  include `answer-extra.md`, etc.).
- `file_size('some/path')` — file size in bytes.

## MissingVariablesError

If any Jinja variable used at render time is not found, the collector aggregates
them and raises `MissingVariablesError`. The message lists every missing name in
insertion order. Typical causes:

- Typo in `(§ v_0 §)` when the value is defined as `v0`.
- Value defined in preamble but preamble file not prepended (check that
  `preamble.md` exists at the problem level — the Makefile falls back to a
  no-preamble rule if it's missing).
- Cross-problem reference. Values are scoped to a single problem.

## Common pitfalls

- **Space around `@J`.** It's a line statement *prefix*, not a delimiter. Write
  `@J set …` (with a space). No leading whitespace either — must be column 0.
- **`(§ … §)` in `.jtex` won't work.** The `.jtex` environment uses `(* … *)` for
  variables. Conversely, `(* … *)` in `.md` is a literal `(*` `*)`, not a
  variable.
- **Numeric arithmetic on `PhysicsQuantity` returns `PhysicsQuantity`.** So
  `(§ v0 * 2 §)` becomes `\qty{100}{\metre\per\second}`. If you want a bare number,
  use `.mag` or `|mag`.
- **Ranges (`QuantityRange`) via `%`.** `q1 % q2` constructs a range with `q1` as
  minimum and `q2` as maximum. If `q1 > q2`, pint raises. Prefer the
  `.widen(fraction)` method when you want a symmetric tolerance band.
- **Constants inside math.** `const.g.approx` gives a rounded-magnitude
  `PhysicsQuantity`; use it in expressions. `const.g.symbol` (or `const.g.sym`)
  gives the TeX symbol string. `const.g.full` gives the printable full-precision
  form.
