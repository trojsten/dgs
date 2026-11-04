// What `core/latex/dgs.cls` is for, in the language that sets the page.
//
// It is hand-written and `#import`ed, never generated: a layout decision belongs where it can
// be compiled on its own and read without rendering anything first. What Jinja emits into a
// document is calls into this file carrying values it computed -- `#qty("148", $upright("mm")$)`
// -- and nothing about how they look.
//
// This is a prototype and says so: the page is A4 with seminar's margins, the type is the
// booklet's own, and no attempt is made to reproduce `dgs.cls`'s geometry, heads or tear-offs.

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
#let _number(value) = context {
  let marker = _language().decimal-marker
  let parts = value.split("e")
  let mantissa = parts.at(0).replace(".", marker)
  if parts.len() == 1 {
    math.text(mantissa)
  } else {
    let exponent = parts.at(1)
    if exponent.starts-with("+") { exponent = exponent.slice(1) }
    let power = math.attach(math.text("10"), t: math.text(exponent))
    if mantissa == "" { power } else { math.text(mantissa) + sym.space.thin + sym.times + sym.space.thin + power }
  }
}

#let num(value) = $#_number(value)$

// A number and its unit, thin-spaced, which is what siunitx does and what the booklet prints.
#let qty(value, unit) = $#_number(value) thin unit$

// A bare unit, for `|unit`.
#let unit(unit) = $unit$

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
// The page
// ===========================================================================================

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

// One problem's heading: the title on the left, what it is worth on the right.
#let problem(title, number: none, worth: none) = {
  block(above: 1.2em, below: 0.6em)[
    #set text(size: 1.1em, weight: "bold")
    #if number != none [#number. ]#title
    #if worth != none [#h(1fr) #text(size: 0.85em, weight: "regular")[#worth]]
  ]
}

#let document(
  language: none,
  title: none,
  subtitle: none,
  body,
) = {
  dgs-language.update(language)

  set page(paper: "a4", margin: 15mm, numbering: "1")
  set text(font: "Minion Pro", size: 12pt, lang: language.code)
  set par(justify: true, leading: 0.65em)
  // Typst numbers an equation only when it is told to, and a reference refuses to exist without
  // a numbering -- which is the opposite default from pandoc-crossref and a better one.
  set math.equation(numbering: "(1)")
  // The words a reference uses are the booklet's own, not Typst's: `rovnica 1`, lower case,
  // because that is how the sentence around it reads in these sources.
  set ref(supplement: it => {
    if it.func() == math.equation { language.cref.equation }
    else if it.func() == figure { language.cref.figure }
    else { none }
  })
  set smartquote(quotes: (single: ("'", "'"), double: (language.quotes.open, language.quotes.close)))
  show heading: set block(above: 1.4em, below: 0.8em)

  if title != none {
    align(center)[
      #text(size: 1.6em, weight: "bold")[#title]
      #if subtitle != none [\ #text(size: 1em, weight: "regular")[#subtitle]]
    ]
    v(0.5em)
  }

  show: typography
  body
}
