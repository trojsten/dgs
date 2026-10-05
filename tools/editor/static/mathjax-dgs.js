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
// **Which ones are missing was swept, not guessed.** Of the 200 macros `math.tex` and
// `symbols.tex` define, 66 are written somewhere under `source/` and were absent from here --
// `\Int` 434 times, `\Nuclide` 161, `\Exp` 130, `\Mean` 81, `\Abs` 72, `\Paren` 36. The ones
// below are the subset that translates exactly, with no optional or split argument in the way.
//
// Deliberately still absent, because a MathJax macro would have to lie about them: everything in
// the integral family (`\Int`, `\OInt`, `\IInt` and their suffixed variants take two optionals
// and a differential list), `\Derivative` and `\Eval`, `\Set` and `\Seq` (two optionals each),
// `\Log`, `\Expected`, `\Distribution`, `\Nuclide` and `\Tuple`. Writing them with a fixed
// arity would silently eat the next token in the source, which is worse than a red box saying so.
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
      Earth:   '\\oplus',
      Sun:     '\\odot',
      Moon:    '\\unicode{x263E}',
      Mercury: '\\unicode{x263F}',
      Venus:   '\\unicode{x2640}',
      Mars:    '\\unicode{x2642}',
      Jupiter: '\\unicode{x2643}',
      Saturn:  '\\unicode{x2644}',
      Uranus:  '\\unicode{x2645}',
      Neptune: '\\unicode{x2646}',
      Pluto:   '\\unicode{x2647}',

      // Paired delimiters. `math.tex` declares these through `\DeclarePairedDelimiter` and then
      // calls the *starred* form, which is `\left … \right` -- so the delimiter grows with its
      // content, and writing plain `(#1)` here would print the one thing the macro exists to
      // avoid. `\Dist` sets identically to `\Abs` on purpose: it means the length of a segment
      // rather than an absolute value, and keeps its own name so the two can be told apart later.
      Paren: ['\\left(#1\\right)', 1],
      Abs:   ['\\left\\lvert#1\\right\\rvert', 1],
      Dist:  ['\\left\\lvert#1\\right\\rvert', 1],
      Floor: ['\\left\\lfloor#1\\right\\rfloor', 1],
      Ceil:  ['\\left\\lceil#1\\right\\rceil', 1],
      Dimen: ['\\left[#1\\right]', 1],

      // intervals -- a semicolon between the ends, which is the continental convention and is
      // what `math.tex` writes
      IntervalCC: ['\\left[#1; #2\\right]', 2],
      IntervalCO: ['\\left[#1; #2\\right)', 2],
      IntervalOC: ['\\left(#1; #2\\right]', 2],
      IntervalOO: ['\\left(#1; #2\\right)', 2],

      // `\Must{=}` stacks a `!` over the relation: an equation that *has* to hold.
      Must:      ['\\stackrel{!}{#1}', 1],
      MustEq:    '\\stackrel{!}{=}',
      MustEqual: '\\stackrel{!}{=}',
      MustL:     '\\stackrel{!}{<}',
      MustLL:    '\\stackrel{!}{\\ll}',
      MustG:     '\\stackrel{!}{>}',
      MustGG:    '\\stackrel{!}{\\gg}',
      MustLeq:   '\\stackrel{!}{\\leq}',
      MustGeq:   '\\stackrel{!}{\\geq}',

      // number sets
      Natural:     '\\mathbb{N}',
      NaturalZero: '\\mathbb{N}_0',
      Integer:     '\\mathbb{Z}',
      Rational:    '\\mathbb{Q}',
      Real:        '\\mathbb{R}',
      RealPos:     '\\mathbb{R}^{+}',
      RealNeg:     '\\mathbb{R}^{-}',
      RealNonneg:  '\\mathbb{R}_{\\geq 0}',
      RealNonpos:  '\\mathbb{R}_{\\leq 0}',
      Complex:     '\\mathbb{C}',
      Quaternions: '\\mathbb{H}',
      Domain:      ['\\mathrm{dom}(#1)', 1],

      // statistics
      Mean:     ['\\overline{#1}', 1],
      Var:      ['\\mathrm{Var}\\left(#1\\right)', 1],
      MSE:      ['\\mathrm{MSE}\\left(#1\\right)', 1],
      Bias:     ['\\mathrm{Bias}\\left(#1\\right)', 1],
      Binomial: ['\\binom{#1}{#2}', 2],

      // The nine vulgar fractions, which are a glyph rather than a construction -- see the note
      // in `math.tex` about why there are nine and not more.
      OneHalf:      '\\text{\u00bd}',
      OneThird:     '\\text{\u2153}',
      TwoThirds:    '\\text{\u2154}',
      OneQuarter:   '\\text{\u00bc}',
      ThreeQuarters:'\\text{\u00be}',
      OneEighth:    '\\text{\u215b}',
      ThreeEighths: '\\text{\u215c}',
      FiveEighths:  '\\text{\u215d}',
      SevenEighths: '\\text{\u215e}',

      Exp:  ['e^{#1}', 1],
      Lim:  ['\\lim\\limits_{#1 \\rightarrow #2}', 2],
      Text: ['\\ \\text{#1}\\ ', 1],

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
  // Centred, because `dgs.cls` loads `extarticle` without `fleqn` and so the booklet centres
  // every display. This said `left` from the day the pane first typeset anything, which put the
  // preview out of step with the page it exists to preview.
  chtml: { displayAlign: 'center', mtextInheritFont: true }
};
