r"""
Repairing the archive's SVG labels.

Every figure in the archive was drawn in Inkscape with TeX's own fonts selected by name —
`cmmi12` for maths italic, `cmr12` and `cmr7` for upright text. Those fonts are not installed
here, and **librsvg does not complain**: `fc-match cmmi12` answers *Noto Sans*, so a figure
converts with a clean exit code and the labels come out in the wrong face, upright where they
should be italic.

The repair is a style rewrite and nothing more, because the text content is already correct
Unicode — `α`, `λ`, `F`, `mg` — not cm glyph slots. `cmmi` is maths italic and every label in it
is a variable, so it takes `font-style:italic`; `cmr` is upright. Both become `'Minion Pro'`,
which is what the 145 modern figures in this repository already use.

Three things to know. A `<tspan>` can override its parent `<text>` — `KIN/zavodny_zad.svg` has a
cmmi span inside a cmr text — so every style declaration is treated on its own rather than only
the `<text>` elements. The two rules that need to *read* a label rather than only its font work
per `<text>` element instead, because the family is usually declared on the `<text>` while the
characters live in a child `<tspan>`. And metrics are the residual risk: Minion is narrower than
cmmi and these labels are absolutely positioned, so a label centred on an arrowhead can drift.
Look at the result; a clean exit proves nothing.
"""
import re

HOUSE = "'Minion Pro'"

#: family -> is it maths italic? `cmmi` and `cmsy` are; `cmr` and `cmex` are not.
CM_FAMILIES = {
    'cmmi5': True, 'cmmi7': True, 'cmmi8': True, 'cmmi9': True, 'cmmi10': True, 'cmmi12': True,
    'cmsy7': True, 'cmsy10': True,
    'cmr5': False, 'cmr7': False, 'cmr8': False, 'cmr9': False, 'cmr10': False, 'cmr12': False,
    'cmex10': False, 'cmbx12': False, 'cmti12': True,
}

#: `CM_FAMILIES` is matched case-insensitively. 2009's figures name `cmmi12`, 2010's name
#: `CMR7` and `CMSY10`, and a table keyed on one spelling reports the other as a foreign font
#: and leaves TeX's own maths set in Noto Sans.
CM_FAMILIES = {name.lower(): italic for name, italic in CM_FAMILIES.items()}

#: Families that are already fine, so neither rewritten nor reported.
ACCEPTED = {'minion pro', 'sans-serif', 'serif', 'sans', 'monospace'}

#: A word processor's or drawing program's *default* text font, which is not a choice the way a
#: display face is. Every figure in this repository is set in Minion Pro; these carry labels that
#: were simply typed, so they follow, keeping whatever slant the drawing already declares --
#: 2010's Times New Roman holds `Mg`, `α''`, `r = a - e` and `slnečný lúč` alike, and guessing a
#: slant per label would be inventing where the author already said.
#:
#: A face that *is* a choice -- `Biondi` on a machine's nameplate, `Reprise Script` on a factory
#: sign -- is not here, stays as drawn, and is reported.
DEFAULT_TEXT_FAMILIES = {'times new roman', 'times', 'arial', 'helvetica', 'book antiqua',
                         'verdana', 'calibri', 'liberation serif', 'nimbus roman',
                         'thorndale amt', 'albany amt', 'comic sans ms'}

#: Symbol-encoded Greek: the font puts the Greek alphabet at the Latin letter positions, so the
#: *text* of such a label is Latin and only the font makes it Greek -- `a` sets α. The four ODG
#: drawings LibreOffice exported carry one, `Mathematica1`, holding the `a` of `KIN/lietadlo`'s
#: `\sin\alpha`. Rewriting the family alone would silently turn that α into a Latin `a`.
#:
#: Every transliteration is reported, because this table is asserted from the Symbol encoding
#: rather than measured from the font, and the source sentence is what confirms it.
SYMBOL_GREEK = dict(zip(
    'abcdefghiklmnopqrstuvwxyz',
    'αβχδεφγηικλμνοπθρστυϖωξψζ'))
SYMBOL_FAMILIES = {'Mathematica1', 'Symbol'}

#: A label that is a single maths variable, in whatever font the drawer reached for. cmmi has no
#: Unicode Greek, so every α, λ, φ, ω and Δ in the archive was typed in a *text* font -- 25 in
#: Times New Roman, two in Comic Sans MS -- and they are variables exactly as the cmmi labels
#: beside them are. So a foreign family goes to Minion Pro when, and only when, its whole label is
#: one such character: a sentence in a foreign font is a design choice and stays.
RE_MATHS_LABEL = re.compile(r'^[A-Za-zΑ-Ωα-ω]\d?$')

#: Upright or italic follows LaTeX's own maths font, since that is what sets the rest of the
#: booklet: lowercase Greek and Latin letters are italic, uppercase Greek (`\Delta`) is upright.
def _slant(label: str) -> str:
    return 'normal' if 'Α' <= label[0] <= 'Ω' else 'italic'


def _declared_slant(chunk: str) -> str:
    """The slant the element already asks for, defaulting to upright as SVG does."""
    m = re.search(r'font-style:\s*([a-zA-Z]+)|font-style="([^"]*)"', chunk)
    found = (m.group(1) or m.group(2)).strip().lower() if m else 'normal'
    return 'italic' if found in ('italic', 'oblique') else 'normal'

#: LibreOffice's export writes one `TextPosition` span per laid-out *line*, all at the same `x`.
RE_PARAGRAPH = re.compile(r'<tspan class="TextParagraph">(.*?)</tspan></text>', re.S)
#: One laid-out line: the positioned span, the styled leaf it wraps, and the characters. These
#: exports always nest exactly this far, so the shape is spelled out rather than matched loosely
#: — a non-greedy body stops at the *inner* `</tspan>` and hands back an unclosed tag.
RE_POSITION = re.compile(r'<tspan class="TextPosition" x="([-\d.]+)" y="([-\d.]+)">'
                         r'(<tspan\b[^>]*>)([^<]*)</tspan></tspan>')

#: One `style="…"` attribute, or one `font-family="…"` XML attribute.
RE_STYLE = re.compile(r'style="([^"]*)"')
RE_ATTR_FAMILY = re.compile(r'font-family="([^"]*)"')
RE_FAMILY = re.compile(r"font-family:\s*'?([^;'\"]+?)'?\s*(?=;|\"|$)")
#: One whole `<text>` element. These never nest.
RE_TEXT = re.compile(r'<text\b.*?</text>', re.S)
#: Any family declaration, in either spelling.
RE_ANY_FAMILY = re.compile(r"""font-family:\s*'?([^;'"]+?)'?\s*(?=;|")|font-family="([^"]*)\"""")


def _families(chunk: str) -> set[str]:
    """Every family named anywhere in one element, in either spelling."""
    return {(m.group(1) or m.group(2)).strip().strip("'")
            for m in RE_ANY_FAMILY.finditer(chunk)}


def _label(chunk: str) -> str:
    """The characters one `<text>` element sets, with the markup taken out."""
    return re.sub(r'<[^>]*>', '', chunk).strip()


def _set_family(chunk: str, slant: str) -> str:
    """Point every family declaration in one element at Minion Pro, with the given slant."""
    spec = f"'Minion Pro, {'Italic' if slant == 'italic' else 'Normal'}'"

    def block(m: re.Match) -> str:
        body = m.group(1)
        if not RE_FAMILY.search(body):
            return m.group(0)
        body = RE_FAMILY.sub(lambda _: f'font-family:{HOUSE}', body)
        # The slant has to be *stated*, not left to default: the drawing may be inheriting an
        # italic from a parent, and a maths label's slant is the whole point of this pass.
        if re.search(r'font-style:\s*[a-zA-Z]+', body):
            body = re.sub(r'font-style:\s*[a-zA-Z]+', lambda _: f'font-style:{slant}', body)
        else:
            body = f'font-style:{slant};{body}'
        if '-inkscape-font-specification:' in body:
            body = re.sub(r"-inkscape-font-specification:\s*'?[^;'\"]*'?",
                          lambda _: f'-inkscape-font-specification:{spec}', body)
        else:
            body += f';-inkscape-font-specification:{spec}'
        return f'style="{body}"'

    chunk = RE_STYLE.sub(block, chunk)
    chunk = RE_ATTR_FAMILY.sub(lambda _: f'font-family="Minion Pro" font-style="{slant}"', chunk)
    return chunk


def _rewrite_style(block: str, others: list[str]) -> tuple[str, int]:
    """One CSS declaration list. Returns the new text and how many families were replaced."""
    m = RE_FAMILY.search(block)
    if not m:
        return block, 0
    family = m.group(1).strip()
    if family.lower() not in CM_FAMILIES:
        if family.lower() not in ACCEPTED:
            others.append(family)
        return block, 0

    italic = CM_FAMILIES[family.lower()]
    block = RE_FAMILY.sub(lambda _: f'font-family:{HOUSE}', block, count=1)
    spec = f"'Minion Pro, {'Italic' if italic else 'Normal'}'"
    if '-inkscape-font-specification:' in block:
        block = re.sub(r"-inkscape-font-specification:\s*'?[^;']*'?",
                       lambda _: f'-inkscape-font-specification:{spec}', block)
    else:
        block += f';-inkscape-font-specification:{spec}'
    want = 'italic' if italic else 'normal'
    if re.search(r'font-style:\s*[a-zA-Z]+', block):
        block = re.sub(r'font-style:\s*[a-zA-Z]+', lambda _: f'font-style:{want}', block)
    else:
        block = f'font-style:{want};' + block
    return block, 1


def _by_label(svg: str) -> tuple[str, list[str]]:
    r"""
    The two rules that have to read a label, not just its font, applied per `<text>` element.

    Symbol-encoded text has its family *and* its characters rewritten, so α stays α. A single
    maths variable in any other foreign font moves to Minion Pro with the slant LaTeX would give
    it. A `<text>` holding anything longer keeps the font it was drawn in — a sentence in
    `Reprise Script` is a design choice, and one letter in `Comic Sans MS` beside two in Times is
    not.
    """
    notes = []

    def element(m: re.Match) -> str:
        chunk, label = m.group(0), _label(m.group(0))
        foreign = {f for f in _families(chunk)
                   if f.lower() not in CM_FAMILIES and f.lower() not in ACCEPTED
                   and not f.endswith(' embedded')}
        if not foreign:
            return chunk
        symbol = foreign & SYMBOL_FAMILIES
        if symbol:
            greek = ''.join(SYMBOL_GREEK.get(c, c) for c in label)
            if greek != label:
                notes.append(f'{", ".join(sorted(symbol))}: {label!r} is Symbol-encoded Greek, '
                             f'read as {greek!r} -- confirm against the problem text')
                chunk = chunk.replace(f'>{label}<', f'>{greek}<')
                label = greek
            return _set_family(chunk, 'italic')
        if RE_MATHS_LABEL.match(label):
            notes.append(f'{", ".join(sorted(foreign))}: the label {label!r} is a single maths '
                         f'variable, set in Minion Pro {_slant(label)} like the rest')
            return _set_family(chunk, _slant(label))
        if all(f.lower() in DEFAULT_TEXT_FAMILIES for f in foreign):
            # The slant is the drawing's own: this face was a default, not a decision, so the
            # family follows the house and nothing else about the label changes.
            return _set_family(chunk, _declared_slant(chunk))
        return chunk

    return RE_TEXT.sub(element, svg), notes


def repair(svg: str) -> tuple[str, list[str], int, list[str]]:
    """
    Rewrite every CM font family in an SVG to Minion Pro.

    Returns the new SVG, any other non-house families still there (reported, never touched — a
    `Comic Sans MS` in a figure may well be the joke), the number of replacements, and any label
    rewritten because of what it says rather than what font it was in.
    """
    others: list[str] = []
    count = 0
    out, labelled = _by_label(svg)

    def style(m: re.Match) -> str:
        nonlocal count
        new, n = _rewrite_style(m.group(1), others)
        count += n
        return f'style="{new}"'

    out = RE_STYLE.sub(style, out)

    def attr(m: re.Match) -> str:
        nonlocal count
        family = m.group(1).strip().strip("'")
        # LibreOffice declares each face twice, once as `<font-face font-family="cmr12 embedded">`
        # in `<defs>`. The suffix is its own; the family behind it is the same one.
        bare = re.sub(r'\s+embedded$', '', family)
        if bare.lower() not in CM_FAMILIES:
            if bare.lower() not in ACCEPTED:
                others.append(bare)
            return m.group(0)
        count += 1
        suffix = ' embedded' if bare != family else ''
        # An XML `font-family` attribute needs its slant as an attribute too: a `font-style` in a
        # parent's CSS would not reach it, and cmmi is maths italic.
        style_attr = ('' if suffix
                      else f' font-style="{"italic" if CM_FAMILIES[bare.lower()] else "normal"}"')
        return f'font-family="Minion Pro{suffix}"{style_attr}'

    out = RE_ATTR_FAMILY.sub(attr, out)
    count += len(labelled)
    return out, _foreign(out), count, labelled


def _foreign(svg: str) -> list[str]:
    """
    Families a reader would still see, which is not the same as families still in the file.

    Three of 2009's figures carry an *empty* `<text>` in Times New Roman that Inkscape left
    behind, and LibreOffice writes a `<font-face font-family="cmr12 embedded"/>` into `<defs>`
    with no `src` to load. Neither puts a glyph on the page, so neither is worth a line in the
    report; what matters is a family that some visible label is actually set in.
    """
    seen: set[str] = set()
    for m in RE_TEXT.finditer(svg):
        if _label(m.group(0)):
            seen |= {f for f in _families(m.group(0))
                     if f.lower() not in CM_FAMILIES and f.lower() not in ACCEPTED}
    return sorted(seen)


def unwrap(svg: str) -> tuple[str, list[str]]:
    r"""
    Undo the line breaks LibreOffice put *inside* a word when it re-laid out an ODG.

    The four ODG drawings were laid out in a text frame sized for the font the author had. With
    that font absent, LibreOffice substitutes a wider one, the frame no longer fits, and it wraps
    — `KIN/kvapky_zad`'s three scale labels came out as `1`/`2`, `2`/`4` and `3`/`0`, one digit
    per line, against the `12`, `24` and `30` the EPS shows was printed.

    A break *inside a word* is the signature, because that is not something a real multi-line
    label does: text wraps at spaces, and only a frame narrower than two characters splits `12`.
    So lines are rejoined only when no line and no join contains whitespace. The rejoined label
    is centred on the lines it replaces, which is where a one-line label sat in a frame the
    author sized for it.

    Every merge is reported. This reads the drawing's intent from its layout, and the EPS beside
    it is what confirms the reading.
    """
    notes = []

    def paragraph(m: re.Match) -> str:
        lines = RE_POSITION.findall(m.group(1))
        if len(lines) < 2 or len(lines) != m.group(1).count('class="TextPosition"'):
            return m.group(0)
        xs = {x for x, _, _, _ in lines}
        bodies = [body for _, _, _, body in lines]
        if len(xs) != 1 or any(not b or re.search(r'\s', b) for b in bodies):
            return m.group(0)
        joined = ''.join(bodies)
        ys = [float(y) for _, y, _, _ in lines]
        x, _, leaf, _ = lines[0]
        notes.append(f'wrap: {bodies} was one word `{joined}` before LibreOffice re-wrapped it, '
                     f'rejoined -- check it against the EPS')
        return (f'<tspan class="TextParagraph"><tspan class="TextPosition" '
                f'x="{x}" y="{(min(ys) + max(ys)) / 2:g}">{leaf}{joined}</tspan></tspan>'
                f'</tspan></text>')

    return RE_PARAGRAPH.sub(paragraph, svg), notes
