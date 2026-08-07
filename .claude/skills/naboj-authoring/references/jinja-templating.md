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

This is why you can write things like `(§ result|f0 §)` in `answer.md` and have `result`
come from the problem's `derived:` mapping — every derived quantity is evaluated while the
context is built, before either pass runs.

The second pass matters most for `eq:` fragments: `(§ eq.foo|disp §)` expands
on pass 1 to a display equation whose body still contains raw `(§ … §)` tags
(the ones defined in the `eq:` YAML value); pass 2 evaluates those inner tags.
Without the second pass, `eq:` would be useless.

## Context available in Markdown Jinja

Provided by `core/builder/renderer.py::CLIInterface.build_context`:

- **Not** `id`. The problem id is read from the directory name into the *metadata* context, where
  it becomes the `eq:` label prefix (`{#eq:<pid>:<key>}`), but it is never added to the render
  context — `(§ id §)` raises `MissingVariablesError`.
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
| `|af`, `|af0..9`     | `symbol \approx \qty{…}` fixed — like `|ef` but `\approx`. |
| `|ag`, `|ag0..9`     | Same, general precision.                                  |
| `|mag`               | Extract raw magnitude (pint magnitude, not a string).     |
| `|unit`              | Just the unit, formatted as `\unit{…}`.                   |
| `|sim`               | `.simplify()` — convert to base SI units.                 |
| `|w(value)`, `|widen(value)` | Construct a tolerance range: `x|w(0.05)` → ±5%.   |

Every family exists both bare and suffixed `0`–`9`. Bare means "no precision in
the format spec", i.e. Python's default for that kind: `f` gives six decimals
(`\qty{96.700000}{…}`), `g` gives six significant digits with trailing zeros
dropped (`\qty{96.7}{…}`). In practice the bare `f` forms are rarely what you
want — reach for `|g`, `|eg`, `|ag` or an explicit precision.

`|ef*` vs `|af*` is purely the relation symbol (`=` vs `\approx`); use `|af*`
for rounded numeric results. Both read `q.symbol`, so a quantity without a symbol
raises `MissingSymbolError` rather than printing `None` — set `symbol:` in `values:`
or use `.alias('x')`.

For a `MathObject`:

| Filter        | What it does                                                     |
| ------------- | ---------------------------------------------------------------- |
| *(none)*      | Raw include: the fragment, no delimiters. Splice a named piece into a larger expression. |
| `|raw`        | The same, said explicitly.                                       |
| `|inl`        | Renders `$…$`. Write sentence punctuation **outside** the tag.  |
| `|disp`       | Renders `$$\n    …\n$$ {#eq:<id>}`.                              |
| `|disp('.')`  | Same with trailing punctuation inside the math.                  |
| `|align`      | `$${\n    …\n}$$ {#eq:<id>}` (aligned environment).              |
| `|align(',')` | Same with punctuation.                                           |
| `|dispd`, `|dispc`, `|disps`, `|dispq`, `|dispe` | Shorthands for `|disp` with `.` `,` `;` `?` `!`. |
| `|alignd`, `|alignc`, `|aligns`, `|alignq`, `|aligne` | Ditto for `|align`.     |

Mnemonic: **d**ot, **c**omma, **s**emicolon, **q**uestion mark, **e**xclamation
mark — one suffix per member of `MathObject._INTERPUNCTION`, so the shorthands
cover every punctuation mark the formatter accepts.

The suffixed forms are `functools.partial`s with the punctuation already bound,
so they take **no** argument: `(§ eq|dispd('.') §)` raises `TypeError`.
They exist because `|dispc` reads better than `|disp(',')` in the middle of a
derivation, where nearly every equation ends in a comma or a full stop.

How an equation is delimited is the filter's business, not the fragment's: a bare
`(§ eq.foo §)` yields the LaTeX as written, so it can be dropped inside another equation
(`x = (§ eq.res §)` within an `|align` block), while `|inl` and `|disp` wrap it for use on
its own. Writing `$(§ eq.foo §)$` by hand is therefore no longer needed, and inside display
math it was never valid.

Punctuation rules, enforced in `MathObject.__format__`:

- Accepted trailing punctuation is exactly `. , ; ? !`.
- A bad trailing character after a valid base spec raises `ValueError` naming
  the character; an unknown base spec raises `NotImplementedError`. The two are
  deliberately distinct — the first is the common author typo.
- A bare reference and `|inl` accept no punctuation; write it after the closing `$`.
- `disp` and `align` indent each content line by four spaces and append
  `{#eq:<MathObject.id>}` — this is why `eq:` keys double as label names.

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

All of them work on raw numbers. On a `PhysicsQuantity` most are numpy ufuncs,
which dispatch to a same-named method on the object — so **only the subset that
`PhysicsQuantity` implements works**. Verified behaviour:

| Works on a `PhysicsQuantity`                     | Raises `TypeError` / `AttributeError` |
| ------------------------------------------------ | ------------------------------------- |
| `sin cos tan asin acos atan log deg ceil floor`  | `cbrt log10 log2 exp rad atan2`       |
| `sqrt` (implemented as `x ** 0.5`), `pow`        |                                       |

The failure message is opaque (`loop of ufunc does not support argument 0 of
type PhysicsQuantity which has no callable log10 method`). Fix by taking the
magnitude first: `log10(x|mag)` / `log10(x.mag)`, or add the missing method to
`core/builder/context/quantities/physics_quantity.py`. Note `deg(x)` works but
`rad(x)` does not — asymmetric because only `.degrees()` is implemented.

`sqrt` on a quantity whose unit is not a perfect square yields a fractional
exponent: `sqrt(PQ(4, 'metre'))` → `\qty{2}{\meter\tothe{0.500}}`. That is almost
always an authoring bug; take `.mag` or fix the expression's dimensions.

Constructors (short aliases in parentheses):

```
PQ(magnitude, unit)            # ad-hoc PhysicsQuantity, e.g. PQ(100, '%')
QuantityList(q1, q2, q3)       # (QL) combine several commensurate quantities into a list
QuantityProduct(q1, q2, q3)    # (QP) combine several commensurate quantities into a product (e.g. box dimensions)
QuantityRange(lo, hi)          # (QR) build a range directly; equivalent to `lo % hi`
```

Both the long names and the short aliases are registered, so `QR(a, b)` and
`QuantityRange(a, b)` are the same global.

`q1 % q2` and `q.widen(v)` remain the idiomatic ways to build a `QuantityRange` (see
quantities-and-constants.md); `QR(lo, hi)` is there for when the operands aren't
bare variables and `%` would need extra parens anyway.

## Units beyond SI

The pint registry lives in `core/builder/jinja.py` and is installed as pint's
*application* registry, so every module shares it. Two local extensions:

- **Currency.** `eur` is defined as its own dimension `[currency]`, with `€` and
  `EUR` as symbols; a preprocessor rewrites a literal `€` in unit strings to
  `EUR`. So `PQ(3, 'eur')|f2` → `\qty{3.00}{\eur}` (`\eur` is declared in
  `core/latex/siunitx.tex`). Currency is not commensurate with anything else, as
  intended.
- **Temperature.** Use `'degC'` for absolute temperatures and `'delta_degC'` for
  differences. `absolute + delta` is fine (`20 °C + 5 Δ°C = 25 °C`), but
  multiplying or dividing an absolute Celsius value raises pint's
  `OffsetUnitCalculusError` — convert with `.to('kelvin')` before doing
  arithmetic that scales it.

### Multi-word units

pint's `Lx` format builds the siunitx macro from the unit's *full name*, so any
multi-word unit comes out as invalid TeX: `au` → `\astronomical_unit`,
`ly` → `\light_year`, `degC` → `\degree_Celsius`. `PhysicsQuantity._latex_unit`
rewrites the ones DGS can render via the `PINT_TO_SIUNITX` table
(`physics_quantity.py`) — currently au, light year, tonne, electronvolt, Celsius
and ΔCelsius, Fahrenheit, rpm, atmosphere, atomic mass unit, pixel, `\gforce`,
watt-hour — and raises `UnknownUnitMacroError` for everything else, rather than
emitting a `\foo_bar` that only blows up later in the XeLaTeX log.

So `PQ(1, 'au')|f2` → `\qty{1.00}{\au}`, and it composes:
`.to('au/year')` → `\unit{\au\per\year}`. But `'nautical_mile'`, `'psi'`,
`'tropical_year'`, `'ft_lb'`, … raise. Two ways out:

- Spell the unit out instead of using pint's compound alias — `'m/s'` renders
  fine, while `'mps'` (one pint unit called `meter_per_second`) raises. Likewise
  `'km/h'` not `'kph'`.
- If the unit genuinely belongs in a problem, `\DeclareSIUnit` it in
  `core/latex/siunitx.tex` and add the pint name to `PINT_TO_SIUNITX`.

## Computing values — `derived:`, not `@J set`

Computed quantities live in the `derived:` mapping in `meta.yaml`, evaluated in document
order before anything is rendered:

```yaml
derived:
  result:       'v0**2 / const.g.approx - sqrt((v0**4 / const.g.approx**2) - D**2)'
  result_exact: 'v0**2 / const.g - sqrt((v0**4 / const.g**2) - D**2)'
```

See `layout.md` for the details (ordering, quoting, error reporting). Idiomatic pattern:
compute a rounded-constant version for `answer.md` and an exact-constant version for
`solution.md`.

`@J set` in a `preamble.md` still works and is the escape hatch for the rare computation
that needs real control flow, but it is no longer the everyday tool: a loop can nearly
always be unrolled into a few named `derived:` steps.

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
- Value defined in `derived:` but misspelled at the use site (or vice versa).
- Value defined in a `preamble.md` that was not prepended — the Makefile falls back to a
  no-preamble rule when the file is absent, so a typo'd filename fails this way.
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
