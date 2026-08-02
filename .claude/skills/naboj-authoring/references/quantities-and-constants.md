# Physics quantities and constants

DGS wraps `pint` in a `PhysicsQuantity` class (`core/builder/context/quantities/`)
that carries a symbol, a magnitude, a unit, and optional `si_extra` settings for
`siunitx` formatting. Constants and per-problem `values` are all instances of
`PhysicsQuantity` (constants are `PhysicsConstant`, a subclass).

## Declaring values in `meta.yaml`

```yaml
values:
  v0:
    magnitude: 50
    unit: 'metre / second'          # pint expression: use spaces or /, ^, *, ()
    symbol: 'v_0'                    # TeX (will appear inside $…$)
  D:
    magnitude: 70
    unit: 'metre'
    symbol: 'd'
  f:
    magnitude: 0.3
    unit: ~                          # ~ or '1' → dimensionless
  frac:
    magnitude: 96
    unit: '%'                        # percent unit
  acc:
    magnitude: 2.6
    unit: 'kilometre / hour / second'
    si_extra:                        # forwarded to siunitx as [key=value, …]
      per-mode: repeated-symbol
    symbol: a
  m_c:
    magnitude: 20
    unit: 'kilogram'
    symbol: "m_c"
```

- `magnitude:` accepts int, float, or scientific literal. For explicit floats in
  YAML use `!!float 1e-6` if you hit a parsing corner case.
- `unit:` is a pint unit expression. Common tokens: `metre`, `second`,
  `kilogram`, `newton`, `joule`, `pascal`, `mole`, `kelvin`, `ampere`, `volt`,
  `ohm`, `watt`, `hertz`, `radian`, `degree`. Compose with `*`, `/`, `**`, `squared`,
  `cubed`, `per`. Example: `'kilogram * metre / second squared'`.
- `symbol:` is the TeX symbol used by `.eq`, `.equals`, `|ef`, `|eg`. Include
  LaTeX escapes if you need them: `symbol: "v_{\\mathrm{max}}"` (YAML requires the
  escape doubling), or single-quote raw: `symbol: 'g_{\Moon}'`.
- `si_extra:` becomes `[key1=value1, key2=value2]` inside the emitted `\qty`
  command. Rare — needed only for unusual per-mode/parse settings.

Dimensionless values are useful for coefficients (friction, efficiency). Their
`\qty{…}{}` reduces to `\num{…}`.

## Referring to a value in Markdown

Just the name — no `values.` prefix:

```
The initial speed is $(§ v0 §)$ and the distance is $(§ D §)$.
```

Renders (approximately) to:

```
The initial speed is $\qty{50}{\metre\per\second}$ and the distance is $\qty{70}{\metre}$.
```

## Properties of `PhysicsQuantity`

Access via dotted attribute (inside `(§ … §)`):

| Attribute       | Result                                                      |
| --------------- | ----------------------------------------------------------- |
| `q.mag`         | Raw pint magnitude (float / int / array).                   |
| `q.unit`        | Pint unit object.                                           |
| `q.symbol`, `q.sym` | The TeX symbol (string). `None` if not set.            |
| `q.eq`, `q.equals` | `"<symbol> = <full>"`. Example: `"v_0 = \qty{50}{...}".` |
| `q.full`        | Default-format string (like `|g`).                          |
| `q.to('unit')`  | Convert to another commensurate unit; returns new quantity. |
| `q.simplify()`  | Convert to base SI units.                                   |
| `q.only_unit()` | Just the unit as `\unit{…}` (siunitx).                      |
| `q.widen(v)`    | Return a `QuantityRange` of `[(1−v)q, (1+v)q]`.             |
| `q.alias('x')`  | Copy of the quantity with a different symbol (keeps unit, `si_extra`, `force_f`). |
| `q.approximate(n)` | Truly round the magnitude to `n` significant digits. Available on any quantity, not just constants — `const.g.approx` is just `approximate(digits)`. |

Arithmetic operators all work: `+ - * / ** neg`. Mixed with raw numbers you get
the expected pint behaviour. `q1 % q2` is overloaded: it constructs a
`QuantityRange(q1, q2)` — do **not** expect Python modulo.

`q.to(...)` takes a unit — a string (`q.to('cm')`), a pint unit object
(`q.to(other.unit)`), or a pint `Quantity`. Passing a **`PhysicsQuantity`**
(`q.to(other)`) fails with an unhelpful `AttributeError: 'NoneType' object has
no attribute 'items'`; write `q.to(other.unit)` instead.

The symbol is the one mutable part: `q.symbol = 'x'` (also `q.sym`, `q.s`)
works, everything else is immutable. Prefer `.alias('x')` in templates, since it
returns a value instead of a statement.

## Extra properties on `PhysicsConstant`

Constants (`const.g`, `const.G`, ...) add:

| Attribute                 | Result                                                 |
| ------------------------- | ------------------------------------------------------ |
| `const.g.approx`          | Rounded to the constant's declared `digits:`; still a  |
|                           | `PhysicsQuantity`. Example: `g ≈ 9.80665 → 9.81`.     |
| `const.g.digits`          | Preferred precision integer.                            |
| `const.g.full`            | Default-format printable form.                          |
| `const.g.full_exact`      | Full precision (`{:99g}`).                              |
| `const.g.full_approx`     | Full precision at `digits`.                             |
| `const.g.fullf(p)`        | Fixed-precision printable.                              |
| `const.g.fullg(p)`        | General-precision printable.                            |
| `const.g.exact`           | `True` if the value is defined as exact.                |

The idiomatic pattern (see `preamble.md` in `archery`, `ice-ice-baby`, etc.):

```
@J set result       = expr(v0, D, const.g.approx)      # for answer.md
@J set result_exact = expr(v0, D, const.g)             # for solution.md
```

Constants come from `core/data/constants.yaml`. Each entry:

```yaml
gforce:
    symbol:     "g"
    aliases:    ['g']
    magnitude:  9.80665
    unit:       "metre / s^2"
    digits:     1
    force_f:    true                    # force |f formatting regardless
```

Aliases mean `const.g` and `const.gforce` refer to the same object. Common
aliases in constants.yaml:

- `const.g`  → `gforce`
- `const.G`  → `gravity` (gravitational constant)
- `const.c`  → `speed_light`
- `const.h`  → `planck`
- `const.hbar` → `planck_bar`
- `const.k`  → `boltzmann`
- `const.NA` → `avogadro`
- `const.R`  → `universal_gas`
- `const.e`  → `elementary_charge`
- `const.m_E`, `const.M_Sun`, etc.

Adding a new constant: edit `core/data/constants.yaml`, keep the thematic grouping
(`### Fundamental`, `### Material`, ...), provide `symbol`, `magnitude`, `unit`,
`digits`, and any `aliases`. Set `exact: true` if the SI defines the value exactly
(planck, c, elementary charge, ...).

Details that are easy to get wrong:

- **`magnitude` should carry full known precision; `digits` is only the default
  print precision.** Rounding belongs in `digits` / `.approx`, never in the
  stored magnitude — that is why commits keep raising precision in place
  (`density_water: 998 → 999.972` with `digits: 3`).
- **Trailing zeros in the magnitude are meaningful to authors, not to Python.**
  `1.3330` and `1.333` parse identically; the zero documents the intended
  precision alongside `digits: 4`.
- **`digits` defaults to 3** when omitted (`PhysicsConstant.__init__`).
- **`unit: ~` means dimensionless** and formats via `\num{…}` instead of `\qty`.
  Refractive indices and dimensionless coefficients use this.
- **`exact: true` is currently metadata only.** It is stored on the constant and
  readable as `const.x.exact`, but no formatter consumes it — don't expect it to
  change output.
- **`force_f: true`** makes `PhysicsConstant.format()` use `.{digits}f` instead
  of `.{digits}g`, so the value never goes scientific. Used for `gforce`.
- Units are pint expressions here too, and the mixed styles in the file
  (`'metre / s^2'`, `'watt / metre squared / kelvin^4'`) all work.

## Formatting filters (summary; full list in jinja-templating.md)

- `|f2` — fixed-decimal with 2 digits: `\qty{50.00}{\metre\per\second}`.
- `|g3` — general with 3 significant digits.
- `|n` — `\num{50}` (no unit).
- `|nf2`, `|ng3` — `\num{}` with precision.
- `|ef2` — `v_0 = \qty{50.00}{...}` (uses `.symbol`).
- `|eg3` — general precision variant.
- `|af2`, `|ag3` — same, but with `\approx` instead of `=`.
- All four (`|ef |eg |af |ag`) also exist bare, meaning Python's default for the
  kind: `f` → six decimals, `g` → six significant digits. Prefer an explicit
  precision or the `g` forms.
- `|mag` — raw magnitude only (for further arithmetic).
- `|unit` — just `\unit{...}`.
- `|sim` — simplify to base units.
- `|w(0.05)` — construct `QuantityRange` = ±5% band around this value.

For a raw Python `float` result of an expression (e.g. `(§ v0**2/D §)`), the same
filters apply — `PhysicsQuantity` handles the routing.

## Ranges (`QuantityRange`)

Three constructors:

- `q1 % q2` where `q1 <= q2` (units must be commensurate; second is converted to
  first's unit).
- `q.widen(v)` — returns a symmetric ±v range around `q`.
- `QuantityRange(lo, hi)` (short alias `QR`) — same as `lo % hi`, spelled out;
  handy when `lo`/`hi` are compound expressions where `%` would need parens.
- Given a range `r`, `r.widen(v)` **widens** the range by factor `(1+v)`
  around its centre. It never narrows; degenerate ranges (min == max) stay
  degenerate.

Format:

- Formatted as `\qtyrange{lo}{hi}{unit}` (or `\numrange{}` for dimensionless).
- Precision inherited from format spec: `|f2`, `|g3`, ...
- `r.to('cm')` converts both endpoints (`QuantityList.to` and
  `QuantityProduct.to` do the same for every element).
- The constructor coerces `maximum` into `minimum`'s unit, so `QR(Q(1,'kg'),
  Q(500,'g'))` is fine, but `minimum > maximum` after coercion raises
  `ValueError` and incompatible units raise pint's `DimensionalityError`.
- `si_extra` of both endpoints is `strict_merge`d (`core/utilities/dicts.py`):
  identical assignments coalesce, conflicting ones raise `ValueError` instead of
  silently picking one.

Typical use in `answer-interval.md`:

```
$(§ (result % result_exact) | w(0.01) | f2 §)$
```

This says: take the range with endpoints `result` and `result_exact`, widen by
1%, format each endpoint to 2 decimals. The narrowest form of tolerance authoring.

## Lists (`QuantityList`)

If you have several commensurate values to typeset as a list:

- Construct with the `QuantityList` global (short alias `QL`): `QuantityList(q1, q2, q3)` or `QL(q1, q2, q3)`.
- Format: `\qtylist{v1;v2;v3}{unit}` (or `\numlist` for dimensionless).
- All values are coerced to the first's unit; `pint` raises on incompatible units.
- Behaves like a sequence of its (coerced) elements: `len(ql)`, `for q in ql`,
  `ql[0]`.
- `ql.to('cm')` returns a new list with every element converted.
- Not commonly used in Náboj; more common in scholar / seminar modules.
- No `.widen()` — unlike a single value or a range, "widening" a list of
  arbitrary points has no single natural meaning, so it's intentionally
  unsupported. Widen each element individually before listing if needed.

## Products (`QuantityProduct`)

For dimensions of an object (e.g. the length x width x height of a box), all
sharing one unit:

- Construct with the `QuantityProduct` global (short alias `QP`): `QuantityProduct(q1, q2, q3)` or `QP(q1, q2, q3)`.
- Format: `\qtyproduct{v1 x v2 x v3}{unit}` (or `\numproduct` for dimensionless).
- Same unit-coercion, `si_extra`-merge, and sequence behavior (`len()`,
  iteration, indexing) as `QuantityList` — the only difference is the `x`
  separator and command name.
- No `.widen()`, for the same reason `QuantityList` has none.

## Common pitfalls

- **Percentages.** `unit: '%'` gives you a `pint` percent. `Q(100, '%')` is
  the ad-hoc form. Convert with `.to('1')` when you need a dimensionless ratio.
- **Angles.** `unit: 'degree'` for degrees; use `.to('radian')` or `rad(x)` in
  Jinja math expressions.
- **Rounding vs. formatting.** `.approx` **truly rounds** the internal magnitude
  (still `PhysicsQuantity`). `|f2` only affects the printed string. For
  `const.g`, use `.approx` when you want subsequent arithmetic to see the rounded
  value (i.e. the value competitors would use).
- **Symbol propagation across arithmetic.** `q1 * q2` produces a new
  `PhysicsQuantity` with `symbol=None`. If you need a labelled result, either
  provide the symbol separately in the math (`$H = (§ result|f2 §)$`), or
  construct via `PhysicsQuantity(...)` with a `symbol=` kwarg.
- **`force_f: true`.** Some constants are declared with this so that they always
  format as fixed decimal even under `|g`. Notable: `gforce`.
- **Immutability.** `PhysicsQuantity` is immutable — you cannot assign to
  `q.quantity`. Construct a new one via `.to()`, `.simplify()`, or arithmetic.
