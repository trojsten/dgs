# Custom LaTeX macros (DGS)

Every non-vanilla-amsmath command you see in Náboj Markdown comes from
`core/latex/*.tex` and is loaded via `core/latex/dgs.cls`. Grep those files
before assuming a macro exists or defining a new one.

Files:

- `core/latex/dgs.cls`   — class definition; package loads; document parameters.
- `core/latex/fonts.tex` — Minion Pro + math font setup.
- `core/latex/math.tex`  — differentials, derivatives, integrals, gradient/div/rot,
                            vectors, sums/products, intervals, statistics.
- `core/latex/symbols.tex`— planets, nuclides.
- `core/latex/siunitx.tex`— siunitx global setup + custom units.
- `core/latex/hacks.tex`  — pandoc/lists fixes, `\phi ↔ \varphi` swap, jigsaw,
                            `\st` for markdown strikeout.
- `core/latex/utilities.tex` — `\URL`, `\errorMessage`, `\protectedInput`,
                                `\exampleIO`.

## Delimiters and brackets

`\left(...\right)` is redefined via `mleftright` (`\mleft`, `\mright`) so spacing
around parentheses no longer requires manual `\!` corrections.

Sized delimiters:

- `\Paren{expr}`     → `\left(expr\right)`
- `\Abs{expr}`       → `\left| expr \right|` — an absolute value or a magnitude
- `\Dist{AB}`        → the same bars, but meaning the length of a segment. Use it whenever the
                       argument is two point names rather than an expression; it has its own
                       paired delimiter, so the two can be distinguished later without touching
                       any call site.
- `\Floor{expr}`     → `\lfloor…\rfloor`
- `\Ceil{expr}`      → `\lceil…\rceil` (also enforced in answer files — see
                       `Adam_ISIC` result `\Ceil{t}`)
- `\ExpectedChevrons{X}[sub]` → `\langle X \rangle_{sub}` — the optional is a **subscript**,
                                not a `\mid` clause. `\ExpectedE{X}[sub]` is `\mathrm{E}[X]_{sub}`,
                                and `\Expected` forwards to `\ExpectedE`. Every module
                                repoints `\Expected` in its `.static/format-override.tex`.

- `\Eval{f}{a}[b]`  → `\left.f\right|_a^b`; `\EvalP` and `\EvalB` are the `(…)` and `[…]`
                       versions.
- `\Dimen{X}`       → `[X]` (dimension brackets).

Tuples and coordinates:

- `\Tuple{a;b;c}`    → `(a; b; c)`  — round brackets
- `\Coord{x;y;z}`    → `[x; y; z]`  — square brackets

The optional argument is the **output** separator, not the input one: the input is always split
on `;`, so `\Coord[,]{x;y}` sets `[x, y]`.

### When to reach for `\Paren`

`\Paren` is the default. It is `\dgsparen@*`, and mathtools' star is the auto-scaling variant —
`\mathopen{}\mathclose\bgroup\left( … \right)`, whose wrapper makes the group `\mathopen`/
`\mathclose` instead of the `\mathinner` a bare `\left(…\right)` would be. Exposing only the
star means no call site ever picks a size.

Writing `\left(…\right)` by hand is **not wrong** here: `math.tex` maps `\left` and `\right` to
mleftright's `\mleft`/`\mright`, which apply the same wrapper. `\Paren` is that, spelled shorter
and in one place.

Plain `()` stays correct for anything single-height that will remain so — an argument list,
`I(t)`, `\sin(2\pi f t)`, `2\pi (Y + a)`. Its spacing is right by construction (`(` is an opening
atom). What it cannot do is grow, silently: the day the content becomes a `\frac` or a `\sqrt`,
the parentheses stay text-height and nothing complains. Three other exceptions: a pair split
across `\\` or `&` needs `\left( … \right.` by hand; auto-scaling that overshoots wants
`\bigl(…\bigr)`; and `\IntP`, `\IIntP`, `\SumP`, `\DrvP` already parenthesise their argument.

## Differentials and derivatives

Base differentials (each includes the standard math-space adjustment):

- `\Diff  x`  → `\mathrm{d}\, x`
- `\PDiff x`  → `\partial\, x`
- `\FDiff x`  → `\Delta\, x`
- `\UDiff x`  → `\delta\, x`

A power and a subscript are written **where the maths writes them**, as embellishments, in
either order and either one alone:

- `\Diff^2{x}`                  → `\mathrm{d}^{2} x`
- `\FDiff_{\mathrm{vap}}{H}`    → `\Delta_\mathrm{vap} H` — an enthalpy of vaporisation
- `\FDiff^2_{\mathrm{vap}}{H}`  → both

**`\Diff[2]{x}` is retired and now stops the build** with `does not take a bracketed argument`.
The old optional scanned forward for `[`, so `\FDiff [A]` — a concentration, an interval, a
bracketed unit — was swallowed as a superscript and set as `\Delta^A`. The guard is deliberate:
without it that mistake is silent.

Derivatives (fraction style controlled by an optional `<d|t|s|n|f>`):

- `\Derivative[order]{f}{x}`         (aliases `\Drv`)
- `\PDerivative[order]{f}{x}`        (`\PDrv`)
- `\FDerivative`, `\UDerivative`     — for Δ- and δ-based derivatives
- `\Derivative<d>[2]{f}{x}`          — with display-style fraction
- `\DerivativeParen[order]{f}{x}`    — d/dx (f) form (`\DrvP`, `\PDrvP`, ...)
- `\DerivativeEmpty[order]{x}`       — d/dx alone (`\DrvE`, `\PDrvE`, ...)
- `\DerivativeEval[order]{f}{x}{a}`  — evaluated at x=a via `\Eval{…}{…}` (`\DrvEval`),
                                       and `\PDerivativeEval` for the partial
- `\Drv{f}{x,y}` — a **comma list** in the denominator: `\frac{\diff f}{\diff x \diff y}`.
  The separator is `\cdiff`'s optional argument, so `\Drv{f}{x;y}` needs `\cdiff[;]`.

## Integrals

The naming scheme: `\Int` is the base 1-D form; the modifiers are
- `I`  = integrand takes a differential-of-power operand
- `D`  = dot product with `d…`
- `C`  = cross product with `d…`
- `V`  = auto-vectorise inputs (`\vec{}`) — **except** in `\IIIntV` and `\IIIntPV`,
         where it means *volume*, i.e. a `\diff^{3}` differential. The letter carries
         two meanings; the 3-D family is the odd one out.
- `O`  = closed loop (single-integral) — `\oint`
- `II` = double integral — `\iint`
- `III`= triple integral — `\iiint`
- `OII`= closed surface (double) — `\oiint`

1-D:
- `\Int[a][b]{f(x)}{x}`             → `\int_a^b f(x) \diff x`
- `\IntP[a][b]{f(x)}{x}`            → adds `\left(…\right)` around integrand
- `\IntX[a][b]{expr}`               → no `\diff`, for algebraic manipulation
- `\IntE[a][b]{}{x}`                → `\int_a^b \diff x` (empty integrand)
- `\IntD[a][b]{\vec E}{\vec r}`     → dot product with `d\vec r`
- `\IntDV[a][b]{E}{r}`              → auto-vec: same as IntD with `\vec{}`
- `\IntC`, `\IntCV`                 → cross product variants

Loop:
- `\OInt[C]{f}{x}`                  → `\oint_C f \diff x`
- `\OIntD[C]{\vec E}{\vec r}`, `\OIntDV[C]{E}{r}`
- `\OIntC`, `\OIntCV`               → cross product

Surface (double):
- `\IIntI[S][…]{f}[power]{x}`       → `\iint_S f \diff^{power} x`
- `\IIntD[S][…]{\vec E}{\vec S}`, `\IIntDV[S][…]{E}{S}`
- `\IIntC`, `\IIntCV`
- `\OIIntD`, `\OIIntDV`, `\OIIntC`, `\OIIntCV` — closed surface

Volume (triple):
- `\IIInt[V][…]{f}{x}{y}{z}`        → `\iiint_V f \diff x \diff y \diff z`
- `\IIIntV[V][…]{f}{r}`             → `\iiint_V f \diff^{3} r`
- `\IIIntPV[V][…]{f}{r}`            → with `\left(…\right)` around integrand

## Vector calculus

- `\Grad`, `\Div`, `\Rot`, `\Laplacian` — with `∇`.
- `\GradT`, `\DivT`, `\RotT`           — text forms (`grad`, `div`, `rot`).
- `\GradV{X}`, `\DivV{X}`, `\RotV{X}`  — auto-vectorised argument.

## Vectors

- `\ArrowVector{X}` / `\vv{X}`         — small arrow (esvect).
- `\LongVector{X}`                     — long arrow (`\overrightarrow`).
- `\BoldVector{X}`                     — bold.
- `\UnitVector{X}`                     — `\hat{\vec{X}}`.
- `\UnitBoldVector{X}`                — `\hat{\BoldVector{X}}`.
- `\UnitArrowVector{X}`               — `\hat{\ArrowVector{X}}`.

`\vec{…}` is the default in DGS; the alternatives are for specific styles. **What `\vec`
means is set per module** in `.static/format-override.tex`: `naboj/phys`, `naboj/chem` and
`naboj/test` map it to `\ArrowVector`, `seminar/FKS` to `\BoldVector`, and `scholar/TA1`,
`scholar/STA` and `naboj/fks-naboj` set nothing, so there it is LaTeX's own accent.

Matrices and their operations: `\Mat{A}` (bold, same output as `\BoldVector`), `\Inv{A}`
→ `A^{-1}`, `\Transpose{A}` → `A^{\top}`.

## Aggregates (Σ, Π, ⋃, ⋂)

Use these instead of raw `\sum`, `\prod`, `\bigcup`, `\bigcap`, `\bigtimes`
(`mdcheck` rules `sum` and `int` enforce it):

- `\Sum[lo][hi]{elt}`                 — Σ with limits
- `\SumP[lo][hi]{elt}`                — same with `\left(…\right)` around body
- `\Product[lo][hi]{elt}`             — Π
- `\CartesianProduct[lo][hi]{elt}`    — big ×
- `\Union[lo][hi]{elt}`               — ⋃
- `\Intersection[lo][hi]{elt}`        — ⋂

Non-aggregate:

- `\Uni` (∪), `\Intersect` (∩), `\union`, `\intersection`.

## Max/min operators

- `\Max[cond]{expr}`, `\Min[cond]{expr}` — with `\underset`-style condition.

## Sets, sequences, intervals

- `\Set{a,b,c}[cond][power]`          — `\{ … \}` with optional sub/superscript.
- `\Seq{a,b,c}[cond][power]`          — parenthesised sequence.
- `\Natural`, `\NaturalZero`, `\Integer`, `\Rational`, `\Real`, `\RealPos`,
  `\RealNeg`, `\RealNonneg`, `\RealNonpos`, `\Complex`, `\Quaternions`.
- `\IntervalCC{a}{b}`  → `[a; b]`     — closed–closed
- `\IntervalCO{a}{b}`  → `[a; b)`     — closed–open
- `\IntervalOC{a}{b}`  → `(a; b]`
- `\IntervalOO{a}{b}`  → `(a; b)`

Note the semicolon separator inside intervals (Slovak convention). Consistent
with `\Tuple`, `\Coord`.

## Text-in-math and phrase spacing

- `\Text{…}`                  — one small space on each side.
- `\QText{…}`                 — `\quad` on each side.
- `\QQText{…}`                — `\qquad` on each side.
- `\Operation{op}`            — right-side annotation (`& \qquad / op`) for
                                 aligned equations.

Do **not** wrap punctuation in `\text{}` (linter rule `pun`).

## Common relations

- `\Implies`   → `\quad\Rightarrow\quad` (use everywhere instead of `\implies` /
                                          `\Rightarrow`).
- `\Iff`       → `\quad\Leftrightarrow\quad`.
- `\ImpliedBy` → `\quad\Leftarrow\quad`.
- `\MustEq`, `\MustL`, `\MustLL`, `\MustG`, `\MustGG`, `\MustLeq`, `\MustGeq`
  — over-stacked with `!` (must-equal etc.).
- `\DefEqual`  → `\stackrel{\mathrm{def}}{=}`.
- `\Assign`    → `\coloneqq`.
- `\Must{X}`   — generic must-something (over-stacked `!`).
- `\MustEqual` is `\MustEq` under a longer name; the sources use it seven times as often.
- `\LAnd`, `\LOr`, `\LXor`, `\LNand` → `\quad\land\quad` and friends.
- `\Uni`, `\Intersect` (and `\union`, `\intersection`, the same two symbols again).

## Functions and miscellany

- `\Lim{x}{0}`   → `\lim\limits_{x \rightarrow 0}`.
- `\Exp{x}`      → `e^{x}`.
- `\Log{x}`, `\Log[2]{x}` → `\log x`, `\log_2 x`.
- `\Domain{f}`   → `\mathrm{dom}(f)`.
- `\Angle`       → `\sphericalangle` (∢, not `\angle`).
- `\kth{4}`      → `4^{\text{th}}` — English only, so not for translated prose.
- `\sinc`, `\hav`, `\erf`, `\arccot`, `\arccsc`, `\atantwo` — operators amsmath lacks.
  There is no `\arcsec`.
- `\omicron`     — the letter LaTeX omits (mathspec supplies the capitals, `\Chi` among them).

## Display-style array columns

`array` sets its cells in text style, so a `\frac` inside one comes out at script size.
`\begin{array}{LCR}` is `\begin{array}{>{\displaystyle}r…}` — upper case because `l`, `c` and `r`
are taken and mean text style. The `arr` filter writes the prefixes itself for an equation
hoisted into `eq:`; these are for a solution that writes `\begin{array}` by hand.

## Statistics

- `\Mean{X}` → `\overline{X}`.
- `\Var{X}`, `\MSE{X}`, `\Bias{X}`.
- `\Binomial{n}{k}` → `\binom{n}{k}`.
- `\Distribution{Name}[var]{params}` → `Name(var \mid params)`.
- `\Dimen{X}`  → `[X]` (dimension brackets).

## Number literals

Fractions and units (safe to write in math or inline text):

- `\OneHalf`, `\OneThird`, `\TwoThirds`, `\OneQuarter`, `\ThreeQuarters` — use
  these instead of Unicode `½`, `⅓`, etc.

Asymptotics:

- `\SmallO{n^2}`, `\BigO{n^2}`, `\BigTheta{n^2}`.

## Symbols

Planets and celestial bodies (see `symbols.tex`):

- `\Sun`, `\Mercury`, `\Venus`, `\Earth`, `\Moon`, `\Mars`, `\Jupiter`, `\Saturn`,
  `\Uranus`, `\Neptune`, `\Pluto`.

Nuclides (via mhchem, defined in `math.tex`, not `symbols.tex`):

- `\Nuclide[A][Z]{sym}` — e.g. `\Nuclide[99m]{Tc}`, `\Nuclide[235][92]{U}`.
- `\Concentration{X}` → `[X]`. Write this rather than a literal bracket: a display row may not
  *begin* with `[`, because `\\` takes an optional length and `\\[B]` dies on `Missing number`
  inside an `array`.

## Chemistry (chem module)

Loaded in `dgs.cls`:

- `\ce{H2O}` — reactions and formulas (mhchem, version 4 with `formula=mhchem`).
- `\chemfig{…}` — structural formulas (chemfig package).
- `\chemsetup{formula=mhchem}` is set globally.

## Font swap (`hacks.tex`)

DGS **swaps** `\phi ↔ \varphi` and `\epsilon ↔ \varepsilon` at load time — Minion
Pro's default `\phi` and `\epsilon` glyphs are ugly. Consequences:

- Write `\phi` when you mean φ (looks like `\varphi` in Computer Modern).
- Write `\epsilon` when you mean ε.
- The linter forbids `\varepsilon` outright (rule `vep`) — the swap makes it
  unnecessary.

## Utility macros for content

- `\URL{https://…}`         — `\href{…}{\texttt{…}}` combo.
- `\errorMessage{msg}`      — bright red highlight (used for missing files etc.).
- `\todoMessage{msg}`       — orange highlight.
- `\protectedInput{path}`   — `\input` if it exists, else emit `\errorMessage`.
- `\tryInput{path}`         — `\input` if it exists, else nothing.
- `\cutHere`                — scissors line for tearoff sheets.
- `\exampleIO{input}{output}` — side-by-side verbatim boxes (programming problems).

`\insertPicture` is **legacy** and forbidden by `mdcheck.lip` — use pandoc
image syntax instead.

## Extending macros

- **New physical constants**: `core/data/constants.yaml`. Add `magnitude`, `unit`,
  `symbol`, `digits`, optional `aliases`, `exact`, `force_f`. No LaTeX changes
  needed.
- **New math macro**: prefer `core/latex/symbols.tex` for symbols, `math.tex` for
  operators / delimiters. Use `\NewDocumentCommand` (LaTeX3 syntax) for
  consistency with the existing style.
- **New siunitx unit**: `core/latex/siunitx.tex`, `\DeclareSIUnit{…}{…}`.
- **New Jinja filter**: register in `core/builder/jinja.py::MarkdownJinjaRenderer`
  under `self.env.filters` (define the function in `core/filters/`).
- **New Jinja global**: same file, `self.env.globals`.
- **New style-checker rule**: `core/mdcheck/check.py`, subclass `LineChecker` (or
  add a `check.FailIfFound` entry with a short 3-letter key in
  `core/markdown-check.py::StyleEnforcer.line_errors`).
- **New template block**: `modules/naboj/templates/blocks/`. Remember `.jtex`
  uses `(* … *)` for variables, not `(§ … §)`.
