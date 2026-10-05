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

      // The four differential symbols, in the plain one-argument form the sources mostly write.
      // They are four *different* things and `math.tex` keeps them apart: an ordinary
      // differential, a partial, a finite difference and an inexact one. Collapsing `\FDiff`
      // onto `\Diff` prints `dt` where the physics says `Δt`, which is a change of meaning and
      // not a change of font. `\mathop{}\!` is the spacing `math.tex` gives them.
      Diff:  ['\\mathop{}\\!\\mathrm{d}#1', 1],
      PDiff: ['\\mathop{}\\!\\partial#1', 1],
      FDiff: ['\\mathop{}\\!\\Delta#1', 1],
      UDiff: ['\\mathop{}\\!\\delta#1', 1],
      Sum:   ['\\sum #1', 1]
    }
  },
  options: { renderActions: { addMenu: [] } },

  // The page is set in Minion, and MathJax's own face is a Computer Modern derivative that sits
  // badly beside it -- lighter, and a different century. STIX2 is Times-shaped and drawn for
  // scientific text, so it sits far closer to an oldstyle serif. It is a MathJax 4 font package,
  // which is why the loader asks for version 4.
  //
  // `mtextInheritFont` matters more than the choice of face: `\text{}` is where the units and
  // the translated words live, and those should be the page's own font rather than a maths one.
  output: { font: 'mathjax-stix2' },
  chtml: { displayAlign: 'left', displayIndent: '0', mtextInheritFont: true }
};
