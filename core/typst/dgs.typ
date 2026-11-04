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
//: So the maths is set in a real math font chosen to sit beside Minion: **TeX Gyre Pagella
//: Math**, Palatino's, which carries the closest weight and colour of the candidates -- they
//: were set side by side in a real paragraph before this was chosen, against Garamond-Math
//: (closer in style, visibly lighter), Termes, STIX, Asana and Computer Modern. It is also
//: what the web maths is already set in: `package.json` pulls
//: `@mathjax/mathjax-pagella-font`, so the two routes to a formula now agree about the face.
//:
//: The file is vendored into `assets/fonts/TeXGyrePagella/` beside the text faces that were
//: already there -- it is GUST-licensed, redistributable, and 600 KB -- so the build does not
//: depend on a TeX Live installation for a font.
//:
//: The two places where a math font would be visibly wrong are handled below: **a number and a
//: unit are set in the body font**, as siunitx sets them in the booklet.
//:
//: The exact answer, if anyone ever wants it, is a MATH table built onto Minion Pro -- or
//: Minion Math, which is a commercial font this repository does not have.
#let MATH-FONT = "TeX Gyre Pagella Math"

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
  set text(font: BODY-FONT, size: 12pt, lang: language.code)
  set par(justify: true, leading: 0.65em)
  // The maths, and the listings. `core/latex/fonts.tex` sets the monospace face to Ubuntu Mono
  // and this follows it; the maths cannot follow the booklet and `MATH-FONT` says why at
  // length.
  show math.equation: set text(font: MATH-FONT)
  show raw: set text(font: MONO-FONT, size: 0.9em)
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
