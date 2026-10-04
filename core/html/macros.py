r"""
`core/latex/math.tex` for the web, expanded to plain LaTeX rather than configured into MathJax.

MathJax can be given macros, but not these: `\FDiff` is `e{^_} t[ m` -- an xparse *embellishment*
argument that takes `^` and `_` groups in either order -- and `\Int` takes two leading optionals,
and `\Coord` splits a `;`-separated list at the TeX level. MathJax's `macros` config expresses
one leading optional argument and nothing else, so roughly a fifth of what the sources write
could not be said in it at all.

So the expansion happens in `core/filters/macros.lua`, before the page is written, and what ships
is **plain LaTeX that any renderer can read** -- MathJax today, KaTeX or MathML tomorrow. It is
the same bargain `siunitx.lua` strikes next door and it is testable the same way: against what
`pdflatex` prints with `math.tex` loaded.

Four shapes cover all of it:

`symbol`     no arguments, a literal replacement -- `\Earth` -> `\oplus`
`args N`     N mandatory arguments into a template -- `\Paren{x}` -> `\left(x\right)`
`diff`       the embellishment family -- `\FDiff^2_x{H}` -> `\mathrm{\Delta}^{2}_{x} H`
`opt O M`    O leading optionals then M mandatory -- `\Int[a][b]{f}{x}`

A macro the sources use and this table does not name is a build error, not a silent gap; the
test below is what makes that true.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

MATH_TEX = pathlib.Path('core/latex/math.tex')
SYMBOLS_TEX = pathlib.Path('core/latex/symbols.tex')
TABLE_LUA = pathlib.Path('core/filters/macros-table.lua')

#: The planets, which `symbols.tex` takes from wasysym and ifsym. Unicode has all of them, and a
#: web font is far likelier to carry the character than the reader is to have the package.
PLANETS = {
    'Sun': '☉', 'Mercury': '☿', 'Venus': '♀', 'Earth': None, 'Moon': '☾',
    'Mars': '♂', 'Jupiter': '♃', 'Saturn': '♄', 'Uranus': '♅', 'Neptune': '♆', 'Pluto': '♇',
}

#: `math.tex` defines nine and no more, because MinionPro has glyphs for exactly these.
FRACTIONS = {'OneHalf': '½', 'OneThird': '⅓', 'TwoThirds': '⅔', 'OneQuarter': '¼',
             'ThreeQuarters': '¾', 'OneEighth': '⅛', 'ThreeEighths': '⅜',
             'FiveEighths': '⅝', 'SevenEighths': '⅞'}

#: name -> (shape, *parameters). See the module docstring for the four shapes.
MACROS: dict[str, tuple] = {}

# -------------------------------------------------------------- paired delimiters
# `\DeclarePairedDelimiter` with a starred call is `\left…\right`, which is what MathJax wants
# spelled out; the package itself has no web equivalent.
for name, (left, right) in {
    'Paren': (r'\left(', r'\right)'),
    'Abs': (r'\left\lvert', r'\right\rvert'),
    # the same glyphs as \Abs by design, and a different meaning: the length of a segment
    'Dist': (r'\left\lvert', r'\right\rvert'),
    'Floor': (r'\left\lfloor', r'\right\rfloor'),
    'Ceil': (r'\left\lceil', r'\right\rceil'),
}.items():
    MACROS[name] = ('args', 1, f'{left}#1{right}')

# -------------------------------------------------------------- differentials
# `\diff@` and friends are `\mathop{}\!\mathrm{d}`; the `\mathop{}\!` is spacing that MathJax
# handles on its own, so the symbol is what carries over.
for name, symbol in {'Diff': r'\mathrm{d}', 'PDiff': r'\partial',
                     'FDiff': r'\mathrm{\Delta}', 'UDiff': r'\delta'}.items():
    MACROS[name] = ('diff', symbol)

# -------------------------------------------------------------- integrals
MACROS['Int'] = ('opt', 2, 2, r'\int\limits_{#1}^{#2} #3\,\mathrm{d}#4')
MACROS['IntD'] = ('opt', 2, 2, r'\int\limits_{#1}^{#2} \dfrac{#3}{#4}')
MACROS['IntX'] = ('opt', 2, 1, r'\int\limits_{#1}^{#2} #3')
MACROS['IInt'] = ('opt', 2, 3, r'\iint\limits_{#1}^{#2} #3\,\mathrm{d}#4\,\mathrm{d}#5')
MACROS['IIntI'] = ('opt', 2, 3, r'\iint\limits_{#1}^{#2} #3\,\mathrm{d}#4\,\mathrm{d}#5')
MACROS['IIntDV'] = ('opt', 2, 3, r'\iint\limits_{#1}^{#2} \dfrac{#3}{#4}\,\mathrm{d}#5')
MACROS['OInt'] = ('opt', 2, 2, r'\oint\limits_{#1}^{#2} #3\,\mathrm{d}#4')
MACROS['OIntD'] = ('opt', 2, 2, r'\oint\limits_{#1}^{#2} \dfrac{#3}{#4}')
# `\oiint` is esint's and MathJax has no such symbol: two circles on one integral is the closest
# honest thing, and it is used 70 times in scholar
MACROS['OIIntI'] = ('opt', 2, 3, r'\oint\!\!\!\oint\limits_{#1}^{#2} #3\,\mathrm{d}#4\,\mathrm{d}#5')
MACROS['OIIntDV'] = ('opt', 2, 3,
                     r'\oint\!\!\!\oint\limits_{#1}^{#2} \dfrac{#3}{#4}\,\mathrm{d}#5')

# -------------------------------------------------------------- derivatives
MACROS['Derivative'] = ('opt', 1, 2, r'\dfrac{\mathrm{d}^{#1}#2}{\mathrm{d}#3^{#1}}')
MACROS['PDerivative'] = ('opt', 1, 2, r'\dfrac{\partial^{#1}#2}{\partial#3^{#1}}')
MACROS['Drv'] = ('opt', 1, 2, r'\dfrac{\mathrm{d}^{#1}#2}{\mathrm{d}#3^{#1}}')
MACROS['FDrv'] = ('opt', 1, 2, r'\dfrac{\mathrm{\Delta}^{#1}#2}{\mathrm{\Delta}#3^{#1}}')
MACROS['DrvE'] = ('opt', 1, 1, r'\dfrac{\mathrm{d}^{#1}}{\mathrm{d}#2^{#1}}')
MACROS['DrvEval'] = ('opt', 1, 3, r'\left.\dfrac{\mathrm{d}#1}{\mathrm{d}#2}\right|_{#3}')
MACROS['DerivativeEval'] = ('opt', 1, 3, r'\left.\dfrac{\mathrm{d}#1}{\mathrm{d}#2}\right|_{#3}')

# -------------------------------------------------------------- aggregates and operators
MACROS['Sum'] = ('opt', 2, 1, r'\sum\limits_{#1}^{#2} #3')
MACROS['SumP'] = ('opt', 2, 1, r'\sum\limits_{#1}^{#2} \left(#3\right)')
MACROS['Lim'] = ('args', 2, r'\lim\limits_{#1} #2')
MACROS['Exp'] = ('args', 1, r'\mathrm{e}^{#1}')
MACROS['Log'] = ('opt', 1, 1, r'\log_{#1} #2')
MACROS['Set'] = ('opt', 0, 1, r'\left\{#1\right\}')
MACROS['Tuple'] = ('splitlist', ';', r'\left(', r'\right)')
MACROS['Coord'] = ('splitlist', ';', r'\left[', r'\right]')

# -------------------------------------------------------------- statistics
for name, template in {
    'Mean': r'\overline{#1}', 'Var': r'\mathrm{Var}\left(#1\right)',
    'MSE': r'\mathrm{MSE}\left(#1\right)', 'Bias': r'\mathrm{Bias}\left(#1\right)',
    'Dimen': r'\left[#1\right]', 'UnitVector': r'\hat{#1}',
}.items():
    MACROS[name] = ('args', 1, template)
MACROS['Binomial'] = ('args', 2, r'\binom{#1}{#2}')
MACROS['Distribution'] = ('opt', 1, 2, r'#2\left(#3\right)')
MACROS['Expected'] = ('opt', 0, 1, r'\mathrm{E}\left[#1\right]')
MACROS['ExpectedE'] = ('opt', 0, 1, r'\mathrm{E}\left[#1\right]')
MACROS['ExpectedChevrons'] = ('opt', 0, 1, r'\left\langle#1\right\rangle')

# -------------------------------------------------------------- spacing, text, relations
MACROS['Text'] = ('args', 1, r'\ \text{#1}\ ')
MACROS['QText'] = ('args', 1, r'\quad\text{#1}\quad')
MACROS['QQText'] = ('args', 1, r'\qquad\text{#1}\qquad')
MACROS['Eval'] = ('opt', 0, 2, r'\left.#1\right|_{#2}')
MACROS['EvalB'] = ('opt', 0, 2, r'\left[#1\right]_{#2}')
MACROS['Must'] = ('args', 1, r'\stackrel{!}{#1}')
MACROS['Operation'] = ('args', 1, r'#1')
MACROS['Nuclide'] = ('opt', 2, 1, r'\ce{^{#1}_{#2}#3}')
MACROS['Angle'] = ('args', 1, r'\angle#1')

for name, body in {
    'Implies': r'\quad\Rightarrow\quad', 'Iff': r'\quad\Leftrightarrow\quad',
    'ImpliedBy': r'\quad\Leftarrow\quad',
    'LAnd': r'\land', 'LOr': r'\lor', 'LXor': r'\quad\veebar\quad', 'LNand': r'\barwedge',
    'MustEq': r'\stackrel{!}{=}', 'MustEqual': r'\stackrel{!}{=}',
    'DefEqual': r'\equiv', 'Assign': r'\coloneqq',
    'Natural': r'\mathbb{N}', 'Integer': r'\mathbb{Z}', 'Rational': r'\mathbb{Q}',
    'Real': r'\mathbb{R}', 'Complex': r'\mathbb{C}',
    'arccot': r'\operatorname{arccot}', 'arccsc': r'\operatorname{arccsc}',
    'erf': r'\operatorname{erf}', 'sinc': r'\operatorname{sinc}',
    'hav': r'\operatorname{hav}', 'atantwo': r'\operatorname{atan2}',
    'DivTV': r'\vec\nabla\cdot', 'Earth': r'\oplus',
}.items():
    MACROS[name] = ('symbol', body)

for name, glyph in PLANETS.items():
    if glyph is not None:
        MACROS[name] = ('symbol', rf'\text{{{glyph}}}')
for name, glyph in FRACTIONS.items():
    MACROS[name] = ('symbol', rf'\text{{{glyph}}}')

for left, right, name in (('[', ']', 'IntervalCC'), ('[', ')', 'IntervalCO'),
                          ('(', ']', 'IntervalOC'), ('(', ')', 'IntervalOO')):
    MACROS[name] = ('args', 2, rf'\left{left}#1; #2\right{right}'.replace(r'\left[', r'\left[')
                    .replace(r'\right)', r'\right)'))

RE_DEFINED = re.compile(
    r'\\(?:New|Renew)DocumentCommand\s*\{?\\(?P<a>[A-Za-z@]+)'
    r'|\\newcommand\*?\s*\{?\\(?P<b>[A-Za-z@]+)'
    r'|\\DeclareMathOperator\*?\{\\(?P<c>[A-Za-z@]+)')


def defined() -> set[str]:
    """Every macro `math.tex` and `symbols.tex` define, internals included."""
    text = MATH_TEX.read_text() + SYMBOLS_TEX.read_text()
    return {m['a'] or m['b'] or m['c'] for m in RE_DEFINED.finditer(text)}


def used(root: pathlib.Path = pathlib.Path('source')) -> set[str]:
    """Every defined macro the sources write. What the table has to cover."""
    names = set()
    for pattern in ('*.md', 'meta.yaml'):
        for path in root.rglob(pattern):
            if not path.is_file():
                continue
            names.update(re.findall(r'\\([A-Za-z]+)', path.read_text(errors='replace')))
    return names & defined()


def lua_literal(value) -> str:
    if isinstance(value, int):
        return str(value)
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def generate() -> str:
    lines = [
        '-- GENERATED by `python -m core.html.macros`. Do not edit.',
        '--',
        "-- `core/latex/math.tex`'s macros as plain LaTeX, for `core/filters/macros.lua`.",
        '-- Shapes: symbol | args N template | diff symbol | opt O M template | splitlist sep l r',
        'local M = {}',
        '',
        'M.macros = {',
    ]
    for name, shape in sorted(MACROS.items()):
        parts = ', '.join(lua_literal(part) for part in shape)
        lines.append(f'    ["{name}"] = {{{parts}}},')
    lines += ['}', '', 'return M', '']
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    table = generate()
    if args.check:
        if TABLE_LUA.is_file() and TABLE_LUA.read_text() == table:
            print(f'{TABLE_LUA} is up to date')
            return 0
        print(f'{TABLE_LUA} is stale: run `python -m core.html.macros`', file=sys.stderr)
        return 1
    TABLE_LUA.write_text(table)
    missing = sorted(used() - set(MACROS))
    print(f'wrote {TABLE_LUA}: {len(MACROS)} macros')
    if missing:
        print(f'  not covered, and written in the sources: {" ".join(missing)}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
