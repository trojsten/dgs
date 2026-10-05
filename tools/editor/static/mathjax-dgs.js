// The macros this repository's maths uses that MathJax does not define.
//
// It used to carry siunitx too -- all 74 unit macros and the nine commands -- because MathJax
// ships no siunitx and neither `\qty` nor the older `\SI` renders without help. That is gone:
// `core/filters/siunitx.py` now expands siunitx into ordinary TeX before pandoc sees it, so the
// fragments carry `83{,}5\ \text{l}` and any MathJax can read them. A macro shim could never have
// done the whole job anyway -- a list, an angle in `d;m;s` form and an exponent all need the
// argument to be *parsed*, and a macro only pastes it back whole.
//
// What is left is the repository's own vocabulary, from `core/latex/math.tex` and `symbols.tex`.
// Only the forms that a MathJax macro can express are here: `\Diff{x}` yes, `\Diff[2]{x}` and
// `\Coord` no, because those take the optional and split arguments xparse gives them and MathJax
// has no equivalent. Anything missing shows as a red undefined-macro error, which is the truth
// about what a page can render and is worth seeing rather than papering over.
//
// mhchem is MathJax's own and only has to be asked for; it is what makes `\ce{H2O}` work.
//
// Loaded before MathJax, which reads `window.MathJax` as its configuration.

window.MathJax = {
  loader: { load: ['[tex]/mhchem'] },
  tex: {
    packages: { '[+]': ['mhchem'] },
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    macros: {
      // spaced connectives -- `core/latex/math.tex`
      Implies:   '\\quad\\Rightarrow\\quad',
      Iff:       '\\quad\\Leftrightarrow\\quad',
      ImpliedBy: '\\quad\\Leftarrow\\quad',
      LAnd:      '\\quad\\wedge\\quad',
      LOr:       '\\quad\\vee\\quad',

      // a translated word set inside maths
      QText:  ['\\quad\\text{#1}\\quad', 1],
      QQText: ['\\qquad\\text{#1}\\qquad', 1],

      // bodies -- `core/latex/symbols.tex`
      Earth: '\\oplus',
      Sun:   '\\odot',
      Moon:  '\\unicode{x263E}',
      Mars:  '\\unicode{x2642}',

      // differentials, in the plain one-argument form the sources mostly write
      Diff:  ['\\mathrm{d}#1', 1],
      FDiff: ['\\mathrm{d}#1', 1],
      Sum:   ['\\sum #1', 1]
    }
  },
  options: { renderActions: { addMenu: [] } },
  chtml: { displayAlign: 'left', displayIndent: '0' }
};
