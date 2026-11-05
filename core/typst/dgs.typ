// What `core/latex/dgs.cls` is for, in the language that sets the page.
//
// It is hand-written and `#import`ed, never generated: a layout decision belongs where it can
// be compiled on its own and read without rendering anything first. What Jinja emits into a
// document is calls into this file carrying values it computed -- `#qty("148", $upright("mm")$)`
// -- and nothing about how they look.
//
// **The page is the booklet's page, and that was measured rather than approximated.** Every
// length in "The page" below was read off a built FKS round with `pdftotext -bbox` and a scan
// for the two rules, and a Typst round now puts its masthead, its head rule, its title, its
// first problem heading, its first baseline and its foot rule within a point of where the
// LaTeX one puts them. That is a check anybody can repeat, and it is the reason to write the
// numbers down as `dgs.cls`'s own names instead of tuning by eye.
//
// What is still a prototype is what is *missing* rather than what is wrong: the tear-offs, the
// rules page, the semester booklet's imposition and the credits block have no Typst counterpart
// yet, and `document()` therefore takes a round's four pieces and no more.

// ===========================================================================================
// The faces
// ===========================================================================================

//: The booklet's own, from `assets/fonts/` -- `core/latex/fonts.tex` chooses the same three.
#let BODY-FONT = "Minion Pro"
#let MONO-FONT = "Ubuntu Mono"

//: **Minion Pro cannot set the maths, and no option here can make it.**
//:
//: Typst lays maths out from a font's OpenType MATH table -- the constants that say how far a
//: radical's bar sits above its content, how a fraction is spaced, how a big operator grows --
//: and from the Math Alphanumeric Symbols block, which is where a math italic `l` comes from.
//: Minion Pro has neither: `#show math.equation: set text(font: "Minion Pro")` gives
//: `warning: current font is not designed for math` and a page where radicals do not stretch,
//: integrals are the size of an `x` and sums carry their limits beside them rather than under.
//: Listing it before a math font does not help either, because the MATH table is taken from the
//: first family and not per glyph. Measured, all three.
//:
//: What LaTeX does instead is `mathspec`'s trick -- map the math letters onto the *text* font's
//: own glyphs -- which is why the booklet's maths is Minion. Typst has no equivalent.
//:
//: So the maths is set in a real math font chosen to sit beside Minion: **STIX Two Math**,
//: drawn for scientific publishing and carrying by far the largest symbol set of the
//: candidates -- which matters for a repository that writes `\varnothing`, `\oplus` and
//: chemistry. The candidates were set side by side in a real Slovak paragraph before this was
//: chosen, against Pagella (wider, Palatino's), Garamond-Math (closest in style and visibly
//: lighter than the prose), Schola (heavier), Bonum, Termes and Computer Modern.
//:
//: **Berenis ADF Pro Math is not among them although it exists**: it warns
//: `current font is not designed for math` and leaves radicals unstretched and a sum at text
//: size, so its MATH table is incomplete whatever its name says.
//:
//: STIX *Two* rather than the 2013 STIX: the same design, maintained, with better-proportioned
//: radicals. The file is vendored into `assets/fonts/STIXTwo/` with its OFL, so the build does
//: not depend on a TeX Live installation for a font. Pagella Math stays vendored beside it as
//: the nearest alternative, and because the web maths is set in Pagella already
//: (`@mathjax/mathjax-pagella-font`).
//:
//: The two places where a math font would be visibly wrong are handled below: **a number and a
//: unit are set in the body font**, as siunitx sets them in the booklet.
//:
//: The exact answer, if anyone ever wants it, is a MATH table built onto Minion Pro -- or
//: Minion Math, which is a commercial font this repository does not have.
#let MATH-FONT = "STIX Two Math"

// ===========================================================================================
// The language, which the generated `build/core/i18n/<lang>.typ` supplies
// ===========================================================================================

// Everything that varies by language and is not Typst's own: the decimal marker, the quotes,
// the one-letter words, the words a reference uses. `#document` puts the table here and the
// functions below read it, so a quantity written inside a fragment gets the document's
// language without being told about it.
#let dgs-language = state("dgs-language", none)

#let _language() = {
  let table = dgs-language.get()
  if table == none {
    panic("no language table: the document must call `document(language: …)` first")
  }
  table
}

// ===========================================================================================
// Quantities
// ===========================================================================================
//
// `core/builder/context/quantities/backend.py` hands these a magnitude as a *string* and a unit
// as finished maths. The string is deliberate: how a number is written -- the decimal marker,
// the exponent -- follows the language, and the language is known here and not there.

// `6.674e-11` becomes `6.674 × 10^(-11)`, and a bare mantissa gives the power alone, so that
// `1e15` is `10^15` and not `1 × 10^15`.
// A number is set in the body font, not in the math font: siunitx does the same in the booklet
// (`mathlf`, Minion's lining figures in maths), and digits are the one thing in a formula a
// reader compares directly against the prose around it.
#let _number(value) = context {
  let marker = _language().decimal-marker
  let parts = value.split("e")
  let mantissa = parts.at(0).replace(".", marker)
  let digits(s) = math.text(font: BODY-FONT, s)
  if parts.len() == 1 {
    digits(mantissa)
  } else {
    let exponent = parts.at(1)
    if exponent.starts-with("+") { exponent = exponent.slice(1) }
    let power = math.attach(digits("10"), t: digits(exponent))
    if mantissa == "" { power } else { digits(mantissa) + sym.space.thin + sym.times + sym.space.thin + power }
  }
}

// And so is a unit, for the same reason: `m` in `29,7 m/s` is a symbol the reader reads as a
// word, and siunitx sets it upright in the text font.
#let _unit(unit) = math.text(font: BODY-FONT, unit)

#let num(value) = $#_number(value)$

// A number and its unit, thin-spaced, which is what siunitx does and what the booklet prints.
#let qty(value, unit) = $#_number(value) thin #_unit(unit)$

// A bare unit, for `|unit`.
#let unit(unit) = $#_unit(unit)$

// An angle closes up against its number -- `45°`, not `45 °`. The one unit that does, mirroring
// `\ang` on the LaTeX side and `45°` on the plain one.
#let ang(value) = $#_number(value) degree$

// The aggregates, spelled the way `core/latex/siunitx.tex` sets siunitx to spell them: units
// repeat, a range takes an en dash with spaces around it, a list a comma, a product a times
// sign. They are assembled as *markup* rather than inside one `$…$`, because maths spacing is
// not sentence spacing -- `75 cm–77 cm` is what the one-equation version prints, and the
// booklet prints `75 cm – 77 cm`.
#let numrange(lower, upper) = [#num(lower) – #num(upper)]
#let qtyrange(lower, upper, unit) = [#qty(lower, unit) – #qty(upper, unit)]
#let numlist(values) = values.map(v => num(v)).join(", ")
#let qtylist(values, unit) = values.map(v => qty(v, unit)).join(", ")
#let numproduct(values) = values.map(v => num(v)).join([ × ])
#let qtyproduct(values, unit) = values.map(v => qty(v, unit)).join([ × ])

// ===========================================================================================
// Typography the build inserts, which no pandoc filter is going to insert here
// ===========================================================================================
//
// `core/filters/spacing.lua` does this for the Markdown flavour and the rules are the same: a
// one-letter word must not end a line in five of the languages, and an abbreviation's halves
// belong together. The lists are the language's own -- `core/i18n/<lang>.yaml` -- so nothing is
// transcribed twice.
//
// **The repeated hyphen is missing and is not forgotten.** Five languages repeat a hyphen when a
// word breaks at one (`bielo-` / `-čierny`), which LaTeX does with a discretionary whose
// pre-break list is empty. Typst exposes no discretionary, so there is nothing to emit; a Typst
// source keeps a plain hyphen until there is. See `core/latex/hacks.tex`'s `\rephyphen`.

#let _escape(text) = {
  let out = text
  for character in ("\\", ".", "+", "*", "?", "(", ")", "[", "]", "{", "}", "^", "$", "|") {
    out = out.replace(character, "\\" + character)
  }
  out
}

// A one-letter word and the space after it, in both cases: a sentence opens with `V`, not `v`,
// and the rule is about the word rather than about where it sits. `core/builder/convertor.py`
// derives the same two cases from one listed letter and says why.
//
// The space may be a newline. With the source wrapped at whatever width an author likes, a
// preposition at the end of a line is exactly the case this is for -- and in Typst, as in TeX, a
// newline between two words is an ordinary breakable space.
#let _singles-pattern(singles) = {
  let letters = singles.map(s => _escape(s.slice(0, 1))).join("")
  "\\b[" + letters + upper(letters) + "][ \n]"
}

#let _pair-pattern(pair) = _escape(pair).replace(" ", "[ \n]")

#let _with-singles(singles, body) = {
  if singles.len() == 0 { body } else {
    show regex(_singles-pattern(singles)): it => it.text.slice(0, 1) + sym.space.nobreak
    body
  }
}

#let _with-pairs(pairs, space, body) = {
  if pairs.len() == 0 { body } else {
    show regex("(" + pairs.map(_pair-pattern).join("|") + ")"): it => {
      it.text.split(regex("[ \n]")).join(space)
    }
    body
  }
}

// The three rules together, in the order `Convertor.call_pandoc` lists their filters. Each is a
// no-op for a language that declares nothing, which is how English and Hungarian get nothing:
// `core/i18n/default.yaml` holds no `typography:` at all, deliberately, because a fallback here
// would make one language's prepositions another's.
#let typography(body) = context {
  let table = _language()
  _with-singles(
    table.at("singles", default: ()),
    _with-pairs(
      table.at("nbsp-pairs", default: ()),
      sym.space.nobreak,
      _with-pairs(table.at("thin-pairs", default: ()), sym.space.nobreak.narrow, body),
    ),
  )
}


// ===========================================================================================
// The page: `dgs.cls`'s own geometry, measured off the booklet rather than guessed
// ===========================================================================================
//
// Every length below was read out of a built FKS booklet with `pdftotext -bbox` and a scan for
// the two rules, and the names are `dgs.cls`'s and `base.jtex`'s. The point of writing them as
// named constants is that the next person can check them the same way: a page of this flavour
// and a page of the Markdown one should put their rules and their first baseline in the same
// place, and if they do not, one of these numbers is wrong.

//: `\RequirePackage[left, right, top, bottom = 15mm]{geometry}`, and `includeheadfoot`, so the
//: header and the footer live *inside* that 15 mm rather than outside it.
#let MARGIN = 15mm
#let HEAD-HEIGHT = 20pt                                 // geometry's `headheight`
#let HEAD-SEP = 16pt                                    // geometry's `headsep`
#let FOOT-SKIP = 32pt                                   // geometry's `footskip`
#let TEXT-WIDTH = 210mm - 2 * MARGIN                    // 180 mm, which is what the booklet sets

//: `\renewcommand{\headrulewidth}{0.4pt}`, and the same for the foot.
#let RULE = 0.4pt

//: `colour-url` and `colour-link` in `dgs.cls`, which are the same teal.
#let LINK-COLOUR = rgb(0, 137, 162)

//: extarticle's 12 pt size table, as fractions of the body size, so that `1.2em` here and
//: `\large` there mean the same thing: 14.4, 17.28, 20.74 and 10 pt.
#let LARGE = 1.2em
#let XLARGE = 1.44em
#let XXLARGE = 1.728em
#let FOOTNOTESIZE = 0.833em

//: `\baselineskip` at 12 pt is 14.5 pt and `\parskip` is `1em plus 0.1em`. Typst counts the
//: first as a gap between two lines' edges rather than between their baselines, so the number
//: is not 14.5; it is what makes the measured baselines 14.5 pt apart in Minion Pro.
#let LEADING = 0.55em
#let PARSKIP = 1em

// Which problem we are inside, so that an equation and a figure can be numbered within it the
// way `\numberwithin{equation}{subsection}` numbers them in the booklet -- `(1.1.2)` is the
// second numbered equation of problem 1.1. `problem()` sets it and resets both counters.
#let dgs-problem = state("dgs-problem", none)

//: How many problems have been set, which is only ever asked one question: is this the first?
#let dgs-problems = counter("dgs-problems")

#let _within-problem(n) = context {
  let problem = dgs-problem.get()
  if problem == none { str(n) } else { problem + "." + str(n) }
}

// A fragment that is not there. `\protectedInput`'s red box, which exists because one missing
// problem must not take the other thirty-nine down with it -- volume 19 printed one for years.
//
// Typst cannot make this decision: `#include` of a missing file is a hard error and there is no
// way to test for one or to catch it. So the *template* decides, with Jinja's `path_exists`, and
// calls this when the answer is no.
#let missing-file(path) = block(
  fill: rgb("#ff0000"),
  inset: 4pt,
  radius: 2pt,
  text(fill: white, weight: "bold")[Missing file: #raw(path)],
)

// One problem's heading, which is `base-booklets.jtex`'s `\subsection`: the number set bold and
// 6 pt clear of the title, the title bold beside it, and whatever the booklet puts on the right
// of that line -- what the problem is worth, or who wrote and marked it -- pushed out to the
// margin at body size by a `\hfill`.
//
// It also opens the problem for the numbering above, which is why it resets both counters.
#let problem(title, number: none, worth: none) = {
  dgs-problem.update(number)
  counter(math.equation).update(0)
  counter(figure.where(kind: image)).update(0)

  context {
    // **The first problem sits closer to what is above it**, and that is the booklet's own
    // shape rather than a tweak: every other heading is preceded by a paragraph and therefore
    // by `\parskip`, while the first is preceded by the title block, which `problems.jtex`
    // ends with a `\\[2pt]` and not a `\par`. Typst collapses two spacings to the larger of
    // them instead of adding them, so the distinction has to be made here.
    let above = if dgs-problems.get().first() == 0 { 17pt } else { 29.5pt }
    block(above: above, below: 18.7pt, width: 100%)[
      #set text(size: LARGE, weight: "bold")
      #if number != none [#number#h(6pt)]#title
      #if worth != none [#h(1fr)#text(size: 1em / 1.2, weight: "regular")[#worth]]
    ]
  }
  dgs-problems.step()
}

// The first page's masthead, which is `seminar-booklet-first`'s header: Trojsten on the left,
// the competition's own logo on the right, and between them the competition, the volume and
// the address. It is laid out here rather than in a `page.header` because the LaTeX one is
// taller than `headheight` and pushes the body down the page -- a Typst header never does, so
// the honest way to say the same thing is to put it at the top of the body and pull it up into
// the margin, which is what `document()` does with the `v(-…)` below.
#let masthead(
  competition: none,
  volume: none,
  address: none,
  logo: none,
) = {
  grid(
    columns: (1fr, auto, 1fr),
    align: (left + top, center + top, right + top),
    image("/assets/logo/trojsten/logo.pdf", height: 20mm),
    // Narrower than `base.jtex`'s `0.7\textwidth`, and for a reason that is Typst's: a grid
    // cell clips what overflows it, and the Trojsten logo at 20 mm high is 108 pt wide, which
    // is wider than the 77 pt the LaTeX proportions leave for it. LaTeX merely reports an
    // overfull box and prints the logo anyway. Nothing wraps at either width.
    block(width: 0.55 * TEXT-WIDTH)[
      #set align(center)
      #set par(leading: LEADING, spacing: 0pt)
      #v(5pt)
      #text(size: XLARGE)[#competition]
      #v(10.3pt, weak: true)
      #text(size: LARGE)[#volume]
      #v(15.9pt, weak: true)
      #text(size: FOOTNOTESIZE)[#address]
    ],
    // The competition's logo lives in its own repository, under `.static/`, so a scope that has
    // not got one simply has none -- the template answers that with `path_exists`, the same way
    // it answers a missing fragment.
    if logo == none { none } else { image(logo, width: 30mm) },
  )
}

#let _rule = line(length: 100%, stroke: RULE)

#let document(
  language: none,
  title: none,
  subtitle: none,
  running-head: none,
  masthead: none,
  logo: none,
  email: none,
  web: none,
  body,
) = {
  dgs-language.update(language)

  // `\fancyhead[LO,RE]{logo}` and `\fancyhead[LE,RO]{\textit{competition}}`: the booklet is
  // two-sided -- it is imposed with `pdfbook --short-edge` -- so the logo and the running head
  // swap sides on an even page, and so do the two halves of the footer.
  let outer-inner(outer, inner) = context {
    if calc.odd(here().page()) { (outer, inner) } else { (inner, outer) }
  }

  set page(
    paper: "a4",
    margin: (
      left: MARGIN, right: MARGIN,
      top: MARGIN + HEAD-HEIGHT + HEAD-SEP,
      bottom: MARGIN + FOOT-SKIP,
    ),
    header-ascent: HEAD-SEP,
    // Measured: the foot rule sits 17 pt below the last line of the body.
    footer-descent: 17pt,
    header: context {
      // The first page carries the masthead instead, in the body.
      if here().page() == 1 { return }
      let mark = if logo == none { none } else { image(logo, height: 6mm) }
      let name = text(style: "italic")[#running-head]
      let (left-slot, right-slot) = if calc.odd(here().page()) { (mark, name) } else { (name, mark) }
      grid(
        columns: (1fr, 1fr),
        align: (left + bottom, right + bottom),
        left-slot, right-slot,
      )
      v(4.4pt, weak: true)
      _rule
    },
    footer: {
      // `\href{mailto:…}{\texttt{…}}` and `\URL`, both in `colour-url`.
      let typewriter(target, label) = link(target, text(fill: LINK-COLOUR, font: MONO-FONT, label))
      let address = typewriter("mailto:" + email, email)
      let site = typewriter(web, web)
      _rule
      v(6.7pt, weak: true)
      context {
        let (left-slot, right-slot) = if calc.odd(here().page()) { (address, site) } else { (site, address) }
        grid(
          columns: (1fr, auto, 1fr),
          align: (left, center, right),
          left-slot, counter(page).display(), right-slot,
        )
      }
    },
  )

  set text(font: BODY-FONT, size: 12pt, lang: language.code)
  // `\setlength{\parindent}{0cm}` and `\setlength{\parskip}{1em plus 0.1em}`: the booklet
  // separates paragraphs with space and never indents one.
  set par(justify: true, leading: LEADING, spacing: PARSKIP, first-line-indent: 0pt)
  // The maths, and the listings. `core/latex/fonts.tex` sets the monospace face to Ubuntu Mono
  // and this follows it; the maths cannot follow the booklet and `MATH-FONT` says why at
  // length.
  show math.equation: set text(font: MATH-FONT)
  show raw: set text(font: MONO-FONT, size: 0.9em)
  // `\setDisplaySkips` in `dgs.cls`: 10 pt above and below a display, and `\jot` at 10 pt.
  show math.equation.where(block: true): set block(above: 10pt, below: 10pt)

  // **A display is numbered only where it carries a label**, which is pandoc-crossref's rule on
  // the Markdown side and has to be built by hand here: Typst numbers every block equation it is
  // told to number. So an unlabelled one is rebuilt without a number and the counter is put
  // back, leaving the numbers running over the labelled displays alone. The `numbering != none`
  // test is what stops the rule recursing into its own replacement.
  set math.equation(numbering: n => [(#_within-problem(n))])
  show math.equation.where(block: true): it => {
    if it.at("label", default: none) == none and it.numbering != none {
      math.equation(block: true, numbering: none, it.body)
      counter(math.equation).update(n => n - 1)
    } else {
      it
    }
  }

  // `\numberwithin{figure}{subsection}`, and `caption`'s `format = hang, width = 0.9\textwidth,
  // textfont = it`: the word and the number upright, the caption itself italic, and the whole
  // thing in a nine-tenths measure that hangs under its own label.
  set figure(numbering: _within-problem, gap: 10pt)
  show figure: set block(above: 12pt, below: 12pt)
  show figure.caption: it => context {
    let head = [#it.supplement #it.counter.display(it.numbering)#it.separator]
    let whole = head + emph(it.body)
    let measure-width = 0.9 * TEXT-WIDTH
    // `caption`'s `singlelinecheck`: a caption that fits on one line is centred, and only a
    // caption that wraps is set as a hanging block.
    if measure(whole).width <= measure-width {
      align(center, whole)
    } else {
      block(width: measure-width, par(justify: true, hanging-indent: measure(head).width, whole))
    }
  }

  // Typst numbers an equation only when it is told to, and a reference refuses to exist without
  // a numbering -- which is the opposite default from pandoc-crossref and a better one.
  // The words a reference uses are the booklet's own, not Typst's: `rovnica 1`, lower case,
  // because that is how the sentence around it reads in these sources.
  set ref(supplement: it => {
    if it.func() == math.equation { language.cref.equation }
    else if it.func() == figure { language.cref.figure }
    else { none }
  })
  set smartquote(quotes: (single: ("'", "'"), double: (language.quotes.open, language.quotes.close)))
  show heading: set block(above: 1.4em, below: 0.8em)

  // **Vertical space is carried on the blocks, never by a weak `v()` beside one.** A weak
  // `v()` immediately before a block does not collapse with that block's own `above` to the
  // larger of the two -- it replaces it, so a 2 pt strut written for tidiness silently ate the
  // 20 pt a heading had asked for and set the first problem title into the subtitle above it.
  if masthead != none {
    // Up into the margin: the body starts `HEAD-HEIGHT + HEAD-SEP` below the 15 mm margin, and
    // the masthead belongs at the margin itself, exactly where a header would be.
    v(-(HEAD-HEIGHT + HEAD-SEP), weak: false)
    masthead
    // Spacing collapses to the larger of two adjacent values rather than adding them, so the
    // gap under the rule is the only place that can say how far down the title starts.
    block(above: 10.6pt, below: if subtitle == none { 26.2pt } else { 22.7pt }, width: 100%, _rule)
  }

  if title != none {
    // `\titleformat{\section}[hang]{\centering\LARGE}` -- centred and large, and *not* bold.
    block(
      above: 0pt,
      // With no subtitle under it the title carries the whole gap down to the first problem,
      // which is what the solutions booklet does: `problems.jtex` is the only one that fills
      // the subtitle block.
      below: if subtitle == none { 36pt } else { 12pt },
      width: 100%,
      align(center, text(size: XXLARGE)[#title]),
    )
    if subtitle != none {
      block(above: 12pt, below: 0pt, width: 100%, align(center, text(size: 1em)[#subtitle]))
    }
  }

  show: typography
  body
}
