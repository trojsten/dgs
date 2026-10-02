# The Jinja vocabulary

Every filter, global, attribute and `meta.yaml` key an author may write, with an example of each.

**This file is generated.** It is written by `python -m core.builder.reference`, from the table in
`core/builder/reference.py`, and `core/tests/test_reference.py` asserts three things about it: that
the table's names are exactly the names the renderers register, in both directions; that every
example below renders to the output printed beneath it; and that this file matches what the
generator produces. So editing it by hand will be undone, and a filter added without an entry
fails the suite.

Two environments, and they are **disjoint**:

| you are editing | environment | a variable is written | and it has |
|---|---|---|---|
| `.md`, and `.svg` / `.tikz` / `.gp` | `MarkdownJinjaRenderer` | `(§ x §)` | 182 filters, 32 globals |
| `.jtex` | `StaticRenderer` | `(* x *)` | 8 filters, 4 globals |

`|disp` works only in the first and `|upnth` only in the second. Neither renderer sees the
other's table, so the mistake is found by a failed build.

A filter family written `|f0 … |f9` is one function with a precision baked in: `|f2` is `|f` to
two places, and a bare `|f` prints whatever the value has. All 140 of those are
generated, so they behave identically and are documented once, under the root.

## The examples

Every example below is rendered in this context, which is what `example_context()` builds:

| name | value | |
|---|---|---|
| `v` | `\qty{3}{\metre\per\second}` | a given, so **exact** |
| `m` | `\qty{1.5}{\kilo\gram}` | a given |
| `d` | `\qty{5}{\kilo\metre}` | a given |
| `rho` | `\qty{1000}{\kilo\gram\per\metre\cubed}` | symbol `\rho` |
| `E` | `\qty{1.602176634e-19}{\joule}` | small enough to need an exponent |
| `frac` | `1.00356e-4` | dimensionless, and the case `\|e` exists for |
| `alpha` | `\qty{44.15}{\degree}` | an angle |
| `c_s` | `\qty{343}{\metre\per\second}` | a **measured** constant, `digits: 3` -- so `.eq` writes `\approx` |
| `result`, `result_approx` | `64.5663 d`, `64.5665 d` | the pair an answer interval spans |
| `sides` | `QL(1 m, 2 m, 3 m)` | a list |
| `box` | `QP(3 cm, 4 cm, 5 cm)` | a product |
| `eq.kin` | `E_\text{kin} = \frac{1}{2} m v^2` | a `MathObject` |
| `eq.chain` | `a &= b \\ &= c` | a chain, for `\|align` |
| `eq.sys` | `x &+& y &=& 1 \\ x &-& y &=& 0` | a system, for `\|arr` |
| `const.g` | `\qty{9.80665}{\metre\per\second\squared}` | measured, `digits: 2` -- so `.approx` is `9.8` |
| `words.air` | `vzduch` | a `words:` entry |
| `n`, `team`, `people`, `date` | `3`, three names, one author, 2025-10-02 | for the `.jtex` examples |


## Numbers

### `|f` · `|f0` … `|f9`

Fixed notation. The digit is decimal places; bare `|f` prints what the value has.

A quantity comes back as a complete `\qty{}{}`, so do not wrap it in `\num{}` yourself.

    (§ v|f2 §)

produces

    \qty{3.00}{\metre\per\second}

### `|g` · `|g0` … `|g9`

Python's `g`: significant figures, and an exponent only when the number is small or large enough to
need one.

    (§ E|g4 §)

produces

    \qty{1.602e-19}{\joule}

### `|e` · `|e0` … `|e9`

Scientific notation, always. The digit is decimals after the point, as Python's `e` counts them.

`|g` only reaches for an exponent below `1e-5`, so `1.004e-4` comes back from it as `0.0001004`.
This is the family for a value the booklet prints as a power of ten. **It shadows Jinja's own `|e`**
(an alias for `escape`), which is harmless here because the environment sets `autoescape=False`.

    (§ frac|g §) versus (§ frac|e3 §)

produces

    \num{0.000100356} versus \num{1.004e-04}

### `|n`

Wrap in siunitx `\num{}`, as-is.

Idempotent: a quantity already renders as `\num{…}` or `\qty{…}{…}`, and this leaves such a value
alone rather than producing `\num{\num{…}}`, which siunitx cannot parse.

    (§ 0.0072|n §)

produces

    \num{0.0072}

### `|nf` · `|nf0` … `|nf9`

`\num{}` around a fixed-notation number. Idempotent, like `|n`.

    (§ 0.0072|nf3 §)

produces

    \num{0.007}

### `|ng` · `|ng0` … `|ng9`

`\num{}` around a `g`-formatted number.

    (§ 1234.5|ng3 §)

produces

    \num{1.23e+03}

### `|ne` · `|ne0` … `|ne9`

`\num{}` around a number in scientific notation.

    (§ 0.0072|ne2 §)

produces

    \num{7.20e-03}

## A value with its symbol

### `|ef` · `|ef0` … `|ef9`

`<symbol> = <value>`, the value in fixed notation.

The symbol comes from the quantity -- `symbol:` on a `values:` entry, `.alias()` on a `derived:` one
-- so the source writes one tag and not `$v = (§ v §)$`. A quantity with no symbol raises rather
than printing a gap.

    $(§ v|ef1 §)$

produces

    $v = \qty{3.0}{\metre\per\second}$

### `|eg` · `|eg0` … `|eg9`

The same with a `g`-formatted value.

    $(§ E|eg3 §)$

produces

    $E = \qty{1.6e-19}{\joule}$

### `|ee` · `|ee0` … `|ee9`

The same with the value in scientific notation.

    $(§ E|ee2 §)$

produces

    $E = \qty{1.60e-19}{\joule}$

### `|af` · `|af0` … `|af9`

`<symbol> \approx <value>`, the value in fixed notation.

**Which of `|ef` and `|af` is a question about the value, not about the source.** A given declared
as exactly 2 g prints `2` at `|f0` and `2` in full, so nothing was rounded and `=` stands; `|af`
there would assert an approximation nobody made. Where the value *does* decide for itself, write `(§
x.eq §)` and let it.

    $(§ result|af(3) §)$

produces

    $t \approx \qty{64.566}{\day}$

### `|ag` · `|ag0` … `|ag9`

The same with a `g`-formatted value.

    $(§ c_s|ag3 §)$

produces

    $c_s \approx \qty{343}{\metre\per\second}$

### `|ae` · `|ae0` … `|ae9`

The same with the value in scientific notation.

    $(§ E|ae2 §)$

produces

    $E \approx \qty{1.60e-19}{\joule}$

## Plain text, where there is no TeX

### `|txt` · `|txt0` … `|txt9`

The value written out as text -- `3 m/s`, `1000 kg/m³`, `45°` -- in fixed notation.

**For an `.svg` and a `.gp` axis label, and nowhere else.** Those are put on the page by
`rsvg-convert` and gnuplot, which are not TeX, so a `\qty{}{}` there prints its own backslashes. In
Markdown, in a `.tikz`, in an `eq:` entry, siunitx is better at this than any string can be. The
unit comes from pint's own `~P` spec, so a unit that can be computed can be printed.

    (§ rho|txt §)

produces

    1000 kg/m³

### `|txtg` · `|txtg0` … `|txtg9`

The same with the magnitude in Python's `g`, and an exponent written `6.674×10⁻¹¹`.

Worth having rather than leaving to `txt`: fixed notation writes the gravitational constant as
`0.00000000006674`, which is not a label anybody can read at 7pt.

    (§ E|txtg4 §)

produces

    1.602×10⁻¹⁹ J

## Quantities

### `|mag`

The bare magnitude as a number, with no unit and no siunitx call.

A float, not a quantity -- so it is what to reach for when the number has to go into arithmetic a
template does, or into a gnuplot script as a literal.

    (§ v|mag §)

produces

    3

### `|unit`

The unit alone, as siunitx `\unit{…}`, with the magnitude dropped.

    (§ rho|unit §)

produces

    \unit{\kilo\gram\per\metre\cubed}

### `|sim`

Converted to base SI units.

    (§ d|sim §)

produces

    \qty{5000}{\metre}

### `|snap`

`|snap(quantum)`

Round a range outward onto a grid of `quantum`, where the format spec cannot.

`__format__` already moves each end outward to the last place it prints, which is what keeps a
printed band from rejecting a correct answer. This is the same operation with the grid chosen rather
than inferred, because `.0f` is the coarsest a format spec offers and an answer may be good to less
-- one good to four figures in kilometres wants a grid of ten. **Not `widen`:** it moves each end to
the next grid point and no further, and snapping an already-snapped range is a no-op.

    (§ (result % result_approx)|snap(0.5)|f1 §)

produces

    \qtyrange{64.5}{65.0}{\day}

### `|dms`

`|dms(places=3)`

An angle as siunitx `\ang{d;m;s}` -- degrees, arcminutes, arcseconds.

`places` chooses how far to go: 1 degrees, 2 degrees and minutes, 3 with seconds. The rounding
happens once, in the smallest place, and carries upward. It is the same number as the decimal form,
so it belongs in `answer-also.md` rather than replacing it.

    $(§ alpha|dms(2) §)$

produces

    $\ang{44;9;}$

## Maths

### `|raw`

The fragment with no delimiters at all. This is what a bare `(§ eq.x §)` already does, so the filter
exists to say so.

Raw is the default because wrapping a bare fragment is one filter away, while unwrapping a
pre-wrapped one is not possible in a template at all. It is what lets one equation be spliced into
another.

    (§ eq.kin|raw §)

produces

    E_\text{kin} = \frac{1}{2} m v^2

### `|inl`

Inline maths: `$…$`.

Never write `$(§ eq.x §)$` by hand -- that is this filter, spelled longer. Put any sentence
punctuation outside the maths.

    (§ eq.kin|inl §)

produces

    $E_\text{kin} = \frac{1}{2} m v^2$

### `|disp`

`|disp, |disp('.')`

A display block with its `{#eq:…}` label, optionally with trailing punctuation inside the maths.

The label is the `eq:` key, so renaming the key renames the reference. **Whether the label is
emitted is not yours to choose**: the renderer sets it from the file being rendered, against the
module's `equation_numbering`, because a problem statement never numbers its equations. That is what
lets one `eq:` entry serve both the statement and the solution. Inside a list item, chain
`|indent(4)`.

    (§ eq.kin|disp('.') §)

produces

    $$
        E_\text{kin} = \frac{1}{2} m v^2.
    $$ {#eq:demo:kin}

### `|dispd`

Shorthand for `|disp('.')`.

    (§ eq.kin|dispd §)

produces

    $$
        E_\text{kin} = \frac{1}{2} m v^2.
    $$ {#eq:demo:kin}

### `|dispc`

Shorthand for `|disp(',')`.

    (§ eq.kin|dispc §)

produces

    $$
        E_\text{kin} = \frac{1}{2} m v^2,
    $$ {#eq:demo:kin}

### `|disps`

Shorthand for `|disp(';')`.

    (§ eq.kin|disps §)

produces

    $$
        E_\text{kin} = \frac{1}{2} m v^2;
    $$ {#eq:demo:kin}

### `|dispq`

Shorthand for `|disp('?')`.

    (§ eq.kin|dispq §)

produces

    $$
        E_\text{kin} = \frac{1}{2} m v^2?
    $$ {#eq:demo:kin}

### `|dispe`

Shorthand for `|disp('!')`.

    (§ eq.kin|dispe §)

produces

    $$
        E_\text{kin} = \frac{1}{2} m v^2!
    $$ {#eq:demo:kin}

### `|align`

`|align, |align('.')`

A display block wrapping the fragment in `aligned`, for a chain aligned on a single relation.

`aligned` pairs its columns `rl rl rl`, so it is right for a chain with a single relation and for a
grid of independent equations, and **wrong for a chain of two or more relations in one row** -- that
is `|arr`.

    (§ eq.chain|align('.') §)

produces

    $$
        \begin{aligned}
            a &= b \\
            &= c.
        \end{aligned}
    $$ {#eq:demo:chain}

### `|alignd`

Shorthand for `|align('.')`.

    (§ eq.chain|alignd §)

produces

    $$
        \begin{aligned}
            a &= b \\
            &= c.
        \end{aligned}
    $$ {#eq:demo:chain}

### `|alignc`

Shorthand for `|align(',')`.

    (§ eq.chain|alignc §)

produces

    $$
        \begin{aligned}
            a &= b \\
            &= c,
        \end{aligned}
    $$ {#eq:demo:chain}

### `|aligns`

Shorthand for `|align(';')`.

    (§ eq.chain|aligns §)

produces

    $$
        \begin{aligned}
            a &= b \\
            &= c;
        \end{aligned}
    $$ {#eq:demo:chain}

### `|alignq`

Shorthand for `|align('?')`.

    (§ eq.chain|alignq §)

produces

    $$
        \begin{aligned}
            a &= b \\
            &= c?
        \end{aligned}
    $$ {#eq:demo:chain}

### `|aligne`

Shorthand for `|align('!')`.

    (§ eq.chain|aligne §)

produces

    $$
        \begin{aligned}
            a &= b \\
            &= c!
        \end{aligned}
    $$ {#eq:demo:chain}

### `|arr`

`|arr('rclcl'), |arr('rclcl', '.')`

A display block wrapping the fragment in `array`, for a display where more than one column has to
line up. **The column spec is required.**

An array has no sensible default layout, hence the argument. It does three things for you, all of
them `array` defects: every column is put in display style, so a `\frac` does not shrink; the
terminal punctuation lands inside the final cell rather than floating at the array's vertical
centre; and every row separator gets `\jot` of glue, because `array` zeroes the lengths `\openup`
would raise.

    (§ eq.sys|arr('rcrcl', '.') §)

produces

    $$
        \begin{array}{>{\displaystyle}r>{\displaystyle}c>{\displaystyle}r>{\displaystyle}c>{\displaystyle}l}
            x &+& y &=& 1 \\[\jot]
            x &-& y &=& 0.
        \end{array}
    $$ {#eq:demo:sys}

### `|arrd`

`|arrd('rclcl')`

Shorthand for `|arr(columns, '.')`.

    (§ eq.sys|arrd('rcrcl') §)

produces

    $$
        \begin{array}{>{\displaystyle}r>{\displaystyle}c>{\displaystyle}r>{\displaystyle}c>{\displaystyle}l}
            x &+& y &=& 1 \\[\jot]
            x &-& y &=& 0.
        \end{array}
    $$ {#eq:demo:sys}

### `|arrc`

`|arrc('rclcl')`

Shorthand for `|arr(columns, ',')`.

    (§ eq.sys|arrc('rcrcl') §)

produces

    $$
        \begin{array}{>{\displaystyle}r>{\displaystyle}c>{\displaystyle}r>{\displaystyle}c>{\displaystyle}l}
            x &+& y &=& 1 \\[\jot]
            x &-& y &=& 0,
        \end{array}
    $$ {#eq:demo:sys}

### `|arrs`

`|arrs('rclcl')`

Shorthand for `|arr(columns, ';')`.

    (§ eq.sys|arrs('rcrcl') §)

produces

    $$
        \begin{array}{>{\displaystyle}r>{\displaystyle}c>{\displaystyle}r>{\displaystyle}c>{\displaystyle}l}
            x &+& y &=& 1 \\[\jot]
            x &-& y &=& 0;
        \end{array}
    $$ {#eq:demo:sys}

### `|arrq`

`|arrq('rclcl')`

Shorthand for `|arr(columns, '?')`.

    (§ eq.sys|arrq('rcrcl') §)

produces

    $$
        \begin{array}{>{\displaystyle}r>{\displaystyle}c>{\displaystyle}r>{\displaystyle}c>{\displaystyle}l}
            x &+& y &=& 1 \\[\jot]
            x &-& y &=& 0?
        \end{array}
    $$ {#eq:demo:sys}

### `|arre`

`|arre('rclcl')`

Shorthand for `|arr(columns, '!')`.

    (§ eq.sys|arre('rcrcl') §)

produces

    $$
        \begin{array}{>{\displaystyle}r>{\displaystyle}c>{\displaystyle}r>{\displaystyle}c>{\displaystyle}l}
            x &+& y &=& 1 \\[\jot]
            x &-& y &=& 0!
        \end{array}
    $$ {#eq:demo:sys}

## Words inside maths

### `|q`

Wrap a word in `\QText{}` -- `\quad\text{…}\quad`.

For a conjunction joining two terms inside one display. The whole tag is `(§ i18n.andw|q §)`.

    $a (§ words.air|q §) b$

produces

    $a \QText{vzduch} b$

### `|qq`

The same with `\QQText{}` -- the wider of the two, for a word joining two whole equations.

    $a (§ words.air|qq §) b$

produces

    $a \QQText{vzduch} b$

## Building a quantity

### `PQ`

`PQ(magnitude, unit, symbol=None)`

Build a quantity inside an expression.

`values:` is where a quantity a *statement gives* belongs; this is for one a `derived:` expression
needs on the spot, and for the odd literal in a template.

    (§ PQ(9.81, 'm/s^2', symbol='g')|ef2 §)

produces

    g = \qty{9.81}{\metre\per\second\squared}

### `QL`

`QL(q1, q2, ...)  ·  QuantityList(...)`

Several commensurate quantities printed as a list: `1 m, 2 m, 3 m`.

Every element is coerced to the first one's unit on construction, and the unit is repeated on each
-- `list-units = repeat` in `core/latex/siunitx.tex`. Indexable and iterable.

    (§ sides|f0 §)

produces

    \qtylist{1;2;3}{\metre}

### `QP`

`QP(q1, q2, ...)  ·  QuantityProduct(...)`

The same printed as a product -- the dimensions of a box, `3 cm × 4 cm × 5 cm`.

    (§ box|f0 §)

produces

    \qtyproduct{3 x 4 x 5}{\centi\metre}

### `QR`

`QR(minimum, maximum)  ·  QuantityRange(...)`

A span of two commensurate quantities. **Usually written as the `%` operator rather than by name**
-- see below.

A range here is the set of answers a marker accepts, so `__format__` rounds each end **outward** to
the last place it prints: the minimum floored, the maximum ceiled. Rounding to nearest would shrink
the set and turn away correct work. `|snap(q)` chooses the grid where the format spec cannot. `QR`
refuses a reversed range, which is why the smaller endpoint is written first.

    (§ QR(result, result_approx)|f3 §)

produces

    \qtyrange{64.566}{64.567}{\day}

### `%`

`(a % b)`

Builds a `QuantityRange` from two quantities. This is how an answer interval is written; `QR` is
never spelled out.

An `answer-interval.md` is one tag: `$(§ (result % result_approx)|f2 §)$`. Smaller endpoint first --
`%` refuses a reversed range, which is the whole reason the `derived:` pair is named `result` and
`result_approx` that way round and not the other.

    (§ (result % result_approx)|f3 §)

produces

    \qtyrange{64.566}{64.567}{\day}

## Including a file

### `include`

`include('vetranie.py')`

The contents of a file beside the template, verbatim -- so a code listing *is* the runnable program
rather than a second copy of it that goes stale.

The path is relative to the file the tag is written in. Inside a list item, chain `|indent(4)`. Like
`blocks:`, the text comes back as written and the second pass expands it, so an included file may
itself carry tags; unlike `blocks:`, a missing file **raises** rather than resolving to nothing,
because an empty code block compiles perfectly and prints nothing. Write it inside a fence, and it
is highlighted like any other fenced block.

## Mathematics

### `sqrt`

`sqrt(x)`

A square root, as `x ** 0.5` -- so it halves the unit too and a quantity comes back a quantity.

    (§ sqrt(PQ(2, 'm^2'))|f4 §)

produces

    \qty{1.4142}{\metre}

### `cbrt`

`cbrt(x)`

A cube root. `numpy`, so a bare number -- **not** unit-aware the way `sqrt` is.

    (§ cbrt(27)|f0 §)

produces

    3

### `pow`

`pow(x, y)`

`x` to the power `y`. Jinja has `**` too; this is for when a filter chain reads better.

    (§ pow(2, 10)|f0 §)

produces

    1024

### `exp`

`exp(x)`

Euler's number to the power `x`.

    (§ exp(1)|f4 §)

produces

    2.7183

### `log`

`log(x)`

The **natural** logarithm. `log10` and `log2` are the other two.

    (§ log(euler)|f0 §)

produces

    1

### `log10`

`log10(x)`

Base-ten logarithm.

    (§ log10(1000)|f0 §)

produces

    3

### `log2`

`log2(x)`

Base-two logarithm.

    (§ log2(1024)|f0 §)

produces

    10

### `sin`

`sin(x)`

Sine. **Radians** -- wrap a degree figure in `rad()`.

    (§ sin(rad(30))|f3 §)

produces

    0.500

### `cos`

`cos(x)`

Cosine, in radians.

    (§ cos(0)|f0 §)

produces

    1

### `tan`

`tan(x)`

Tangent, in radians.

    (§ tan(rad(45))|f3 §)

produces

    1.000

### `asin`

`asin(x)`

Inverse sine, returning radians.

    (§ deg(asin(0.5))|f0 §)

produces

    30

### `acos`

`acos(x)`

Inverse cosine, returning radians.

    (§ deg(acos(0.5))|f0 §)

produces

    60

### `atan`

`atan(x)`

Inverse tangent, returning radians.

    (§ deg(atan(1))|f0 §)

produces

    45

### `atan2`

`atan2(y, x)`

The two-argument inverse tangent, which gets the quadrant right. `y` first.

    (§ deg(atan2(1, -1))|f0 §)

produces

    135

### `rad`

`rad(degrees)`

Degrees to radians, on a bare number.

    (§ rad(180)|f4 §)

produces

    3.1416

### `deg`

`deg(radians)`

Radians to degrees, on a bare number.

For a *quantity* carrying an angle unit, `|f`/`.to()` already know what to do; this is the
bare-number pair to `rad`.

    (§ deg(pi)|f0 §)

produces

    180

### `ceil`

`ceil(x)`

Round up. **Unit-aware**: a quantity comes back a quantity, a number a number.

`ceil`, `floor` and `round` each dispatch on the operand, which is why a tag may write `ceil(n)`
without knowing whether `n` came from `values:` or from arithmetic.

    (§ ceil(PQ(2.1, 'm'))|f0 §)

produces

    \qty{3}{\metre}

### `floor`

`floor(x)`

Round down, unit-aware.

    (§ floor(PQ(2.9, 'm'))|f0 §)

produces

    \qty{2}{\metre}

### `round`

`round(x)`

Round to nearest, unit-aware. Takes **no** precision -- that is what `|f2` is for.

**Half-to-even**, because it is numpy's: `round(2.5)` is 2 and `round(3.5)` is 4. Where that
matters, say which way you meant with `ceil` or `floor`.

    (§ round(PQ(2.5, 'm'))|f0 §)

produces

    \qty{2}{\metre}

### `gamma`

`gamma(x)`

The gamma function, `math.gamma`.

    (§ gamma(5)|f0 §)

produces

    24

### `beta`

`beta(x, y)`

The beta function, built from three gammas.

    (§ beta(2, 3)|g3 §)

produces

    0.0833

### `pi`

π, as a plain float.

    (§ pi|f5 §)

produces

    3.14159

### `tau`

τ = 2π.

    (§ tau|f5 §)

produces

    6.28319

### `euler`

e, Euler's number. Spelled out because `e` is already a filter.

    (§ euler|f5 §)

produces

    2.71828

## Attributes of a quantity

### `.eq`

`.eq  ·  .equals`

`<symbol> = <value>` or `<symbol> \approx <value>`, **the quantity deciding which**.

Two independent tests, because each catches what the other cannot. The value has to be the true one
-- `const.speed_sound` is 343 m/s, which prints back perfectly and is still not the speed of sound,
and only the declaration knows that -- **and** the figures it prints have to be all of it: `sqrt(2)`
is exact by every declaration on its way there and prints as 1.41421, and only the arithmetic knows
that. `exact` defaults to true, because a number a statement *gives* is exact.

    $(§ v.eq §)$ and $(§ c_s.eq §)$

produces

    $v = \qty{3}{\metre\per\second}$ and $c_s \approx \qty{343}{\metre\per\second}$

### `.apx`

`.apx  ·  .approximately`

`<symbol> \approx <value>` outright, at the quantity\'s `digits:` figures rather than `%g`'s six.

`eq` reaches for `\approx` where the value has earned it; this says so whatever the value thinks.
`eq` prints what it has, `apx` says "to this many figures".

    $(§ c_s.apx §)$

produces

    $c_s \approx \qty{343}{\metre\per\second}$

### `.mag`

The bare magnitude as a float, with no unit and no siunitx call.

A float, not a quantity -- so `.mag` is what a gnuplot script or a `.svg` wants as a literal, and
what arithmetic inside a template wants.

    (§ v.mag §)

produces

    3

### `.unit`

The pint unit object. For the printed unit, use the `|unit` filter.

    (§ rho.unit §)

produces

    kilogram / meter ** 3

### `.s`

`.s  ·  .sym  ·  .symbol`

The declared symbol, as LaTeX, with no value beside it.

**A symbol is declared on the quantity, not written beside it** -- `symbol:` on a `values:` entry,
`.alias()` on a `derived:` one. That is what lets `$(§ x.eq §)$` be one tag rather than `$\rho = (§
rho §)$`.

    $(§ rho.s §)$

produces

    $\rho$

### `.full`

The value and unit at full precision, with no symbol and no relation.

    (§ c_s.full §)

produces

    \qty{343}{\metre\per\second}

### `.to`

`.to('cm')`

Converted to a commensurate unit. Carries the symbol, `digits` and `exact` across.

Usually the last thing a `derived:` expression does, because the unit a result should print in is
rarely the one the arithmetic produced.

    (§ d.to('m')|f0 §)

produces

    \qty{5000}{\metre}

### `.alias`

`.alias('\\rho')`

The same quantity carrying a symbol. This is how a `derived:` entry declares one.

**Four backslashes in a double-quoted YAML scalar**, two in a single-quoted one. Takes no precision
-- digits are declared or they are absent.

    (§ (m / PQ(1, 'm^3')).alias('\\rho').eq §)

produces

    \rho = \qty{1.5}{\kilo\gram\per\metre\cubed}

### `.simplify`

`.simplify()`

Converted to base SI units. The `|sim` filter is the same thing.

    (§ d.simplify()|f0 §)

produces

    \qty{5000}{\metre}

### `.only_unit`

`.only_unit()`

The unit alone as `\unit{…}`. The `|unit` filter is the same thing.

    (§ rho.only_unit() §)

produces

    \unit{\kilo\gram\per\metre\cubed}

### `.approx`

**On a `const.` value only:** the constant rounded to the figures the constants sheet prints.

This is the second of the two admissible values of every constant, and the reason an answer interval
is a span at all: the competitor is holding the sheet, so both that rounding and `constants.yaml`'s
own figure are legitimate arithmetic. A `derived:` pair is `result` computed with `const.g` and
`result_approx` with `const.g.approx`.

    (§ c_s.approx.eq §)

produces

    c_s \approx \qty{343}{\metre\per\second}

### `.exact`

Whether the value is the true one. Spreads through arithmetic as **contamination only** -- `a * b`
is exact only if both are -- and never as a guarantee.

    (§ v.exact §) then (§ c_s.exact §)

produces

    True then False

### `.digits`

How many figures to **print**, or `None`. Presentation, not uncertainty.

It does **not** propagate through arithmetic. A constant shown to one figure because that is what
the constants sheet prints would, if it propagated, claim that precision for everything computed
from it, and an answer of 24.6 mm would print as 20. It travels only where the quantity does: `to`,
`alias`, `simplify`, `approximate`, and a sign.

    (§ c_s.digits §)

produces

    3

### `.printed_digits`

`digits` if it is declared, and the default otherwise -- so it is always a number.

    (§ v.printed_digits §)

produces

    3

### `.prints_exactly`

Whether `.eq` may write `=`: exact **and** round-tripping through its own printed form.

The round-trip allows a thousand ulps rather than demanding equality. A value that is exactly 0.1 by
construction can still be stored a few ulps out -- after solving a linear system, say -- and an
equality test would call it rounded; a value that really was rounded is wrong by nine orders of
magnitude more than that, so the threshold is not a tuned number.

    (§ v.prints_exactly §) then (§ c_s.prints_exactly §)

produces

    True then False

## Attributes of a range, list or product

### `.minimum`

A range's lower endpoint, as a quantity.

    (§ (result % result_approx).minimum|f3 §)

produces

    \qty{64.566}{\day}

### `.maximum`

A range's upper endpoint.

    (§ (result % result_approx).maximum|f3 §)

produces

    \qty{64.567}{\day}

### `.qs`

The elements of a `QL` or a `QP`, as a plain list. They are also indexable and iterable directly.

    (§ sides.qs[1]|f0 §)

produces

    \qty{2}{\metre}

## `.jtex` templates only

### `|roman`

An integer in Roman numerals. 1 to 3999.

    (* n|roman *)

produces

    III

### `|nth`

An English ordinal: `3rd`. Gets the teens right.

    (* n|nth *)

produces

    3rd

### `|upnth`

The same with the suffix superscripted, as maths.

    (* n|upnth *)

produces

    $3^{\mathrm{rd}}$

### `|plural`

`|plural(one, two, many)`

Pick a form by count, on the Slavic one/two-to-four/many split.

    (* n|plural('úloha', 'úlohy', 'úloh') *)

produces

    úlohy

### `|format_list`

`|format_list(and_word='a', oxford_comma=False)`

Join a list with commas and a conjunction before the last item.

    (* team|format_list *)

produces

    Jana Nováková, Peter Novák a Eva Horváthová

### `|format_people`

`|format_people(and_word='a')`

The same over `{name, gender}` entries, which is how `authors:` and `evaluators:` are written. A
nameless entry becomes a red error box rather than a gap.

    (* people|format_people *)

produces

    Jana Nováková

### `|format_gender_suffix`

The Slovak participle ending for one or more people -- `""`, `a`, `o`, `i`.

An undeclared gender gives `\errorMessage{?}`, so a missing `gender:` key is visible on the page
rather than silently masculine.

    pripravil(* people|format_gender_suffix *)

produces

    pripravila

### `|isotex`

A date as `YYYY--MM--DD`, the en dashes already escaped for TeX.

    (* date|isotex *)

produces

    2025--10--02

### `plural`

`plural(how_many, one, two, many)`

The same as the filter, called rather than piped.

    (* plural(n, 'úloha', 'úlohy', 'úloh') *)

produces

    úlohy

### `textbf`

`textbf(x)`

Wrap in `\textbf{}`.

    (* textbf(n) *)

produces

    \textbf{3}

### `path_exists`

`path_exists(path)`

`os.path.exists`, for a template that includes a figure only if it is there.

### `file_size`

`file_size(path)`

`os.path.getsize`. Used to tell an empty generated file from a real one.

## Jinja's own

### `|indent`

`|indent(4)`

Indent every line but the first. **This is how an equation goes inside a list item.**

`disp` and `align` close at column 0 whatever indent the tag sits at, so a bare `(§ eq.x|disp('.')
§)` inside a bullet puts its `$$ {#eq:…}` flush left and breaks out of the list. The defaults are
exactly right: `first=False` because the tag's own indent already covers the opening `$$`, and
`blank=False` so no trailing whitespace is invented. `include()` chains it the same way.

    -   (§ eq.kin|disp('.')|indent(4) §)

produces

    -   $$
            E_\text{kin} = \frac{1}{2} m v^2.
        $$ {#eq:demo:kin}

### `|format`

`|format(a, b)`

Python's `%` interpolation. Mostly seen building a path or an id.

    (§ '%s-%02d'|format('fig', 7) §)

produces

    fig-07

### `|float`

Coerce to a float, with `0.0` on failure. Rarely needed -- `values:` already parses numbers.

    (§ "2.5"|float|f1 §)

produces

    2.5

## Namespaces the context adds

### `const.`

`const.<name>`

The physical constants, from `core/data/constants.yaml`. Reached as `(§ const.g §)`, and their
symbols are already declared.

**A constant has two admissible values, and that is why an answer interval is a span:** the figure
in `constants.yaml`, and the one the constants sheet prints -- that constant's `digits:` applied,
which is what `.approx` returns. The competitor is holding the sheet, so both are legitimate
arithmetic. A value there is **measured unless it says `exact: true`**, which is the opposite
default to a `values:` entry, because a number a statement gives is exact and a measurement is not.

    (§ const.g.eq §) and (§ const.g.approx.eq §)

produces

    g \approx \qty{9.80665}{\metre\per\second\squared} and g \approx \qty{9.8}{\metre\per\second\squared}

### `i18n.`

`i18n.<word>  ·  i18n.words['and']`

The recurring translated words, from `core/i18n/<lang>.yaml`. For a word belonging to one problem,
use `words:` in its meta instead.

`and` and `or` are Jinja keywords, so they are spelled `i18n.andw` and `i18n.orw`; everything else
is spelled as written. `(§ i18n.words['and'] §)` is the older form and still works. **There is no
fallback to English and never was** -- a word a language has not got is boxed in red, reported at
the end of the render, and the render then exits nonzero.

## `meta.yaml`: a problem

### `values:`

`values: {name: {magnitude, unit, symbol, ...}}`

A quantity the **statement gives**. Spread into the top-level namespace, so `values: {h: …}` is
reached as `(§ h §)`.

A bare string, float or int is also accepted and passes through verbatim -- but the name then claims
the text is a number the statement gives, which is what `blocks:` is for instead. `values:` names
are checked against `RESERVED_NAMES` (`blocks`, `const`, `eq`, `i18n`, `words`).

### `derived:`

`derived: {name: "<jinja expression>"}`

A computed quantity. Each value is evaluated as a **Jinja expression**, in document order, so a
later entry sees the earlier ones.

An expression, not a template: anything with two statements in it fails as `TemplateSyntaxError:
chunk after expression`. **An answer belongs here** -- a typed number in `answer.md` is the
`answer-literal` finding, and the answer should be `result` printed as `(§ result §)`, so that
changing an input changes the answer. This is also where `PQ`, `QL` and `.to()` are usually written.

### `eq:`

`eq: {name: "<latex>"}`

A block equation, hoisted out of the per-language files so there is one copy. Reached as `(§
eq.name|disp('.') §)`; **the key becomes the label**, `{#eq:<pid>:<key>}`.

Hoisting removes the per-language latitude a translator has, deliberately: the physics is the same
in every language and copies drift. An equation written out once per language has been known to lose
a minus sign in one of them, so that one booklet told its readers the opposite of what the others
did, and nothing reported it. A troll answer, an argument only prose carries, or a derivation that
genuinely differs per language is worth leaving alone. Long entries wrap as a `|` block scalar --
write `|2` if the first row is indented deeper than the rest.

### `words:`

`words: {term: {lang: text}}`

A word that appears **inside maths** and has to change with the language. Namespaced: `(§ words.air
§)`.

The alternative is a copy of the equation per language, which is how the copies drift apart. A word
belonging to one problem is the common case; a recurring one -- `and`, `or` -- belongs in
`core/i18n/<lang>.yaml` instead. **There is no fallback**: a missing word is boxed in red, every
miss is reported at the end of the render, and the render then exits nonzero.

### `blocks:`

`blocks: {name: |\n  <text>}`

Text that comes back **verbatim**, namespaced as `(§ blocks.name §)`. The one content key that does
nothing to what it holds.

The case it exists for is a gnuplot preamble shared by several plots. **`|`, never `>`** -- a folded
scalar collapses newlines into spaces and gnuplot wants one directive per line. Tags inside a block
are expanded by the second pass, so a preamble can write `tcold = (§ tcold.mag §)` and stay in step.

### `authors:`

`authors: {idea: [...], problem: [...], solution: [...]}`

**Required.** Who did which of the three jobs. Each role is a list of names, possibly empty.

Not read by the renderer; consumed by the audit and by the booklet credits. A **volume** meta
carries an `authors:` too, and it is a different shape -- the booklet's four credit lists rather
than one problem's three roles.

### `tags:`

`tags: [mechanics, ...]`

**Required**, and validated against a fixed vocabulary. May be empty.

### `audit:`

`audit: {ignore: ['answer-literal']}`

Opt a problem out of a named audit check, **with the reason written beside it**.

Some answers are not the output of a calculation and no amount of `derived:` will make them one --
an answer that is 100 % whatever the inputs are, one that is zero by a symmetry, one that names
which of several things is left over. Those cannot satisfy `answer-literal`. The reason written
beside the ignore is the point of the key: an unexplained ignore is indistinguishable from a bug.

### `similar:`

`similar: [other-problem-id]`

**Read by nothing.** In the schema so that a meta carrying it still validates.

### `difficulty:`

`difficulty: 3`

**Read by nothing**, like `similar`.

### `physics:`

`physics: 3`

**Read by nothing**, like `similar`.

### `math:`

`math: 3`

**Read by nothing**, like `similar`.

### `id:`

`id`

**Not written by an author** in a problem meta -- injected from the directory name, and used to
build each equation label.

A **venue** meta does write one, and a competition meta writes its own; the volume and language
levels have theirs injected like a problem.

## `meta.yaml`: a `values:` entry

### `magnitude:`

`magnitude: 9.81`

**Required.** The number.

**Scientific notation must be written `1.0e+15`.** YAML 1.1 wants both a decimal point *and* a sign
before it reads an exponent as a number, so `1e15`, `1e+15` and `1.0e15` all parse as bare
**strings**. The schema rejects a string here for exactly that reason and names the key; before it
did, the first sign of trouble was a `derived:` expression reporting `unsupported operand type(s)
for /`, a long way from the cause.

### `unit:`

`unit: \metre\per\second`

The unit. Defaults to dimensionless.

**Spell it the way pint spells it**, because `values:` and `derived:` render through pint and
anything else blocks a hoist: `\kilo\gram` not `\kilogram`, `\metre\cubed` not `\cubic\metre`,
`\metre` not `\meter`. All three pairs are identical on the page, so this is a source convention --
but a solution writing the unit the other way cannot be pointed at the value holding the same
number, because the rendered output moves.

### `symbol:`

`symbol: \rho`

The LaTeX symbol this quantity is named by. **Defaults to the entry's own name**, which is usually
not what you want.

Declaring it here is what lets the source write `$(§ rho.eq §)$` as one tag instead of `$\rho = (§
rho §)$`.

### `digits:`

`digits: 3`

How many figures to **print**. Presentation only -- independent of `exact`, and it does not
propagate through arithmetic.

### `exact:`

`exact: false`

Whether the value is the true one. **Defaults to `true`** here, because a number a statement gives
is exact.

The opposite default to `constants.yaml`, where a value is measured unless it says otherwise. Set it
false for a given that is itself an approximation.

### `si_extra:`

`si_extra: {per-mode: symbol}`

siunitx options passed through to the `\qty[...]` call.

### `force_f:`

`force_f: true`

Print in fixed notation whatever the format spec asks for.

### `aliases:`

`aliases: [...]`

Alternative names, for a constants file. Accepted on a problem `values:` entry, where nothing reads
it.

## `meta.yaml`: a volume

### `problems:`

`problems: [first-problem, second-problem, ...]`

The volume's running order, and the **only** thing that puts a problem in a booklet.

This list *is* the running order and is what `ContextVolume` iterates. A problem missing from it is
never built; one listed without a directory gets `\protectedInput`'s red `Missing file` box, which
is the intended behaviour -- a hole in a booklet should be loud. The audit checks both directions,
as `unit-unlisted` and `listed-missing`.

### `date:`

`date: 2025-11-14`

The day the competition is held.

### `start:`

`start: 10:00`

When it starts. A **venue** meta may override it with its own.

### `workshop:`

`workshop: ...`

The accompanying workshop, for the booklet.

### `table:`

`table: ...`

The answer table printed at the back of the booklet.

### `constants:`

`constants: [g, c, ...]`

Which constants the sheet prints -- and therefore, through each one's `digits:`, what `.approx` is
allowed to be.

### `venues:`

`venues: {...}`

Venues written inline rather than as their own directories.

### `orgs:`

`orgs: [...]`

Organisers, on a volume or on a venue. The documented legacy escape hatch.

## `meta.yaml`: a language

### `booklet:`

`booklet: ...`

The booklet's own per-language settings, in `<volume>/languages/<lang>/meta.yaml`.

### `translators:`

`translators: [...]`

Who translated this language, for the credits.

## `meta.yaml`: a venue

### `name:`

`name: Bratislava`

The venue, as the booklet prints it.

### `code:`

`code: BA`

The short code that goes into a team number.

### `language:`

`language: sk`

Which language booklet this venue is sent.

### `evaluators:`

`evaluators: [...]`

Who marks there.

## `meta.yaml`: the competition

### `hacks:`

`hacks: ...`

Per-competition overrides, in `source/naboj/<competition>/meta.yaml`.

### `tearoff:`

`tearoff: ...`

The tear-off answer slip.

### `url:`

`url: https://...`

The competition's own address.

### `organisation:`

`organisation: ...`

Who runs it.
