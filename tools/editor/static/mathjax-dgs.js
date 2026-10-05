// siunitx, and this repository's own macros, for MathJax.
//
// **MathJax ships no siunitx at all** -- neither `\\qty` nor the older `\\SI` is defined, and both
// come out as a red undefined-macro error. That is why the HTML branch used to rewrite `\\qty` into
// `\\SI` "for the old failing web": the web once loaded a MathJax 2 third-party extension that knew
// the v2 spelling. Nothing on npm supplies one for MathJax 3 or 4, so the choice is between a
// shim and no units on the page.
//
// This is the shim, and it is generated from what the sources actually emit: the nine siunitx
// commands they use and every one of the unit macros, `core/latex/siunitx.tex`'s custom ones
// included. A unit is a plain substitution, so a prefix composes the way siunitx composes it --
// `\\kilo\\gram` is `k` then `g`.
//
// Three things it deliberately does not do, because a MathJax macro cannot parse its argument:
// a list stays semicolon-separated (`\\qtylist{1;2;3}{\\metre}` reads `1;2;3 m`), an angle in the
// `d;m;s` form keeps its semicolons, and a mantissa written `e+15` stays literal rather than
// becoming a power of ten. Anything else undefined still shows red, which is the truth about what
// the web can render and is worth seeing.
//
// `\\SI` and `\\si` are here beside `\\qty` and `\\unit` deliberately: the pipeline emits the modern
// spelling, and a handful of seminar sources write the old one by hand. Both have to typeset or the
// preview is wrong for one of them.
//
// Loaded before MathJax, which reads `window.MathJax` as its configuration. mhchem is MathJax's
// own and only has to be asked for; it is what makes `\\ce{H2O}` work.

window.MathJax = {
  loader: { load: ['[tex]/mhchem'] },
  tex: {
    packages: { '[+]': ['mhchem'] },
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    macros: {
      "metre": "\\mathrm{m}",
      "meter": "\\mathrm{m}",
      "second": "\\mathrm{s}",
      "gram": "\\mathrm{g}",
      "kilogram": "\\mathrm{kg}",
      "kg": "\\mathrm{kg}",
      "mole": "\\mathrm{mol}",
      "mol": "\\mathrm{mol}",
      "ampere": "\\mathrm{A}",
      "kelvin": "\\mathrm{K}",
      "candela": "\\mathrm{cd}",
      "litre": "\\mathrm{l}",
      "tonne": "\\mathrm{t}",
      "hour": "\\mathrm{h}",
      "minute": "\\mathrm{min}",
      "day": "\\mathrm{d}",
      "year": "\\mathrm{a}",
      "joule": "\\mathrm{J}",
      "newton": "\\mathrm{N}",
      "watt": "\\mathrm{W}",
      "pascal": "\\mathrm{Pa}",
      "volt": "\\mathrm{V}",
      "ohm": "\\Omega",
      "coulomb": "\\mathrm{C}",
      "farad": "\\mathrm{F}",
      "henry": "\\mathrm{H}",
      "tesla": "\\mathrm{T}",
      "hertz": "\\mathrm{Hz}",
      "lumen": "\\mathrm{lm}",
      "lux": "\\mathrm{lx}",
      "gray": "\\mathrm{Gy}",
      "becquerel": "\\mathrm{Bq}",
      "steradian": "\\mathrm{sr}",
      "radian": "\\mathrm{rad}",
      "bel": "\\mathrm{B}",
      "decibel": "\\mathrm{dB}",
      "electronvolt": "\\mathrm{eV}",
      "atomicmass": "\\mathrm{u}",
      "au": "\\mathrm{au}",
      "parsec": "\\mathrm{pc}",
      "lightyear": "\\mathrm{ly}",
      "watthour": "\\mathrm{Wh}",
      "horsepower": "\\mathrm{hp}",
      "rpm": "\\mathrm{rpm}",
      "molar": "\\mathrm{M}",
      "torr": "\\mathrm{Torr}",
      "atmosphere": "\\mathrm{atm}",
      "foot": "\\mathrm{ft}",
      "inch": "\\mathrm{in}",
      "pound": "\\mathrm{lb}",
      "percent": "\\%",
      "ppm": "\\mathrm{ppm}",
      "eur": "\\unicode{x20AC}",
      "gforce": "\\mathit{g}",
      "permille": "\\unicode{x2030}",
      "arcminute": "\\prime",
      "celsius": "{}^\\circ\\mathrm{C}",
      "dcelsius": "{}^\\circ\\mathrm{C}",
      "fahrenheit": "{}^\\circ\\mathrm{F}",
      "yocto": "\\mathrm{y}",
      "zepto": "\\mathrm{z}",
      "atto": "\\mathrm{a}",
      "femto": "\\mathrm{f}",
      "pico": "\\mathrm{p}",
      "nano": "\\mathrm{n}",
      "micro": "\\unicode{xB5}",
      "milli": "\\mathrm{m}",
      "centi": "\\mathrm{c}",
      "deci": "\\mathrm{d}",
      "deca": "\\mathrm{da}",
      "hecto": "\\mathrm{h}",
      "kilo": "\\mathrm{k}",
      "mega": "\\mathrm{M}",
      "giga": "\\mathrm{G}",
      "tera": "\\mathrm{T}",
      "peta": "\\mathrm{P}",
      "exa": "\\mathrm{E}",
      "zetta": "\\mathrm{Z}",
      "yotta": "\\mathrm{Y}",
      "per": "/",
      "squared": "^2",
      "cubed": "^3",
      "cubic": "^3",
      "square": "^2",
      "degree": "^\\circ",
      "qty": [
            "{#1\\,#2}",
            2
      ],
      "num": [
            "{#1}",
            1
      ],
      "unit": [
            "{#1}",
            1
      ],
      "ang": [
            "{#1^\\circ}",
            1
      ],
      "qtyrange": [
            "{#1\\,#3\\text{ – }#2\\,#3}",
            3
      ],
      "numrange": [
            "{#1\\text{ – }#2}",
            2
      ],
      "qtylist": [
            "{#1\\,#2}",
            2
      ],
      "numlist": [
            "{#1}",
            1
      ],
      "qtyproduct": [
            "{#1\\,#2}",
            2
      ],
      "numproduct": [
            "{#1}",
            1
      ],
      "SI": [
            "{#1\\,#2}",
            2
      ],
      "si": [
            "{#1}",
            1
      ],
      "SIrange": [
            "{#1\\,#3\\text{ – }#2\\,#3}",
            3
      ],
      "SIlist": [
            "{#1\\,#2}",
            2
      ],
      "Implies": "\\quad\\Rightarrow\\quad",
      "Iff": "\\quad\\Leftrightarrow\\quad",
      "ImpliedBy": "\\quad\\Leftarrow\\quad",
      "QText": [
            "\\quad\\text{#1}\\quad",
            1
      ],
      "QQText": [
            "\\qquad\\text{#1}\\qquad",
            1
      ],
      "Earth": "\\oplus",
      "Sun": "\\odot",
      "Moon": "\\unicode{x263E}",
      "Mars": "\\unicode{x2642}",
      "Diff": [
            "\\mathrm{d}#1",
            1
      ],
      "FDiff": [
            "\\mathrm{d}#1",
            1
      ],
      "Sum": [
            "\\sum #1",
            1
      ]
}
  },
  options: { renderActions: { addMenu: [] } },
  chtml: { displayAlign: 'left', displayIndent: '0' }
};
