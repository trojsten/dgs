"""
The font encodings these booklets use, as literal tables.

Deliberately literal rather than clever, in the spirit of `units.py`: six standard TeX
encodings, written out, so that a wrong character is a wrong line in a table rather than a
wrong rule in an algorithm.

**The font name names the encoding.** That is the whole point of decoding per font rather
than per document, and it is why `pdftotext` cannot do this: it applies one heuristic table
to every font, so `cmsy`'s minus sign (0x00) and `cmmi`'s Greek both come out as nothing.

    dcr, dcti, dcbx, dc*      T1 / Cork      text, including every accented letter
    cmr, cmbx, cmti, cmsl     OT1            text, but only ASCII-ish
    cmmi                      TeX math italic -- variables, and Greek at the ASCII letters
    cmsy                      TeX math symbols -- the minus sign lives here
    msam, msbm                AMS symbols
    Symbol, Math1             Adobe Symbol

Anything else is reported rather than guessed; see `classify`.
"""

# --- T1 / Cork ---------------------------------------------------------------
#
# The encoding the `dc` fonts use, and the reason the prose survives at all: every accented
# letter Slovak needs is a single code point here, so `á é í ó ú ý ä ô č š ž` decode without
# any coordinate work. Only `ď ľ ť ĺ ŕ` are composites -- see `COMBINING` below.

#: 0x00-0x1F are accents in T1, not control characters. A glyph in this range is a mark that
#: belongs to the letter it sits over; `assemble` reattaches it by x-span.
COMBINING = {
    0x00: '̀',   # grave
    0x01: '́',   # acute
    0x02: '̂',   # circumflex
    0x03: '̃',   # tilde
    0x04: '̈',   # dieresis
    0x05: '̋',   # hungarumlaut
    0x06: '̊',   # ring
    0x07: '̌',   # caron
    0x08: '̆',   # breve
    0x09: '̄',   # macron
    0x0A: '̇',   # dot above
    0x0B: '̧',   # cedilla
    0x0C: '̨',   # ogonek
}

#: T1 0x0D-0x1F: quotes, dashes and the f-ligatures.
_T1_LOW = {
    0x0D: '‚', 0x0E: '‹', 0x0F: '›',
    0x10: '“', 0x11: '”', 0x12: '„',
    0x13: '«', 0x14: '»',
    0x15: '–', 0x16: '—',
    0x17: '',       # compound word mark -- an invisible break, correctly dropped
    0x18: '‰', 0x19: 'ı', 0x1A: 'ȷ',
    0x1B: 'ff', 0x1C: 'fi', 0x1D: 'fl', 0x1E: 'ffi', 0x1F: 'ffl',
}

#: T1 0x80-0xBF: the Central European letters. This is the block that makes Slovak work.
_T1_CE = {
    0x80: 'Ă', 0x81: 'Ą', 0x82: 'Ć', 0x83: 'Č', 0x84: 'Ď', 0x85: 'Ě', 0x86: 'Ę', 0x87: 'Ğ',
    0x88: 'Ĺ', 0x89: 'Ľ', 0x8A: 'Ł', 0x8B: 'Ń', 0x8C: 'Ň', 0x8D: 'Ŋ', 0x8E: 'Ő', 0x8F: 'Ŕ',
    0x90: 'Ř', 0x91: 'Ś', 0x92: 'Š', 0x93: 'Ş', 0x94: 'Ť', 0x95: 'Ţ', 0x96: 'Ű', 0x97: 'Ů',
    0x98: 'Ÿ', 0x99: 'Ź', 0x9A: 'Ž', 0x9B: 'Ż', 0x9C: 'Ĳ', 0x9D: 'İ', 0x9E: 'đ', 0x9F: '§',
    0xA0: 'ă', 0xA1: 'ą', 0xA2: 'ć', 0xA3: 'č', 0xA4: 'ď', 0xA5: 'ě', 0xA6: 'ę', 0xA7: 'ğ',
    0xA8: 'ĺ', 0xA9: 'ľ', 0xAA: 'ł', 0xAB: 'ń', 0xAC: 'ň', 0xAD: 'ŋ', 0xAE: 'ő', 0xAF: 'ŕ',
    0xB0: 'ř', 0xB1: 'ś', 0xB2: 'š', 0xB3: 'ş', 0xB4: 'ť', 0xB5: 'ţ', 0xB6: 'ű', 0xB7: 'ů',
    0xB8: 'ÿ', 0xB9: 'ź', 0xBA: 'ž', 0xBB: 'ż', 0xBC: 'ĳ', 0xBD: '¡', 0xBE: '¿', 0xBF: '£',
}

#: T1 0xC0-0xFF is Latin-1's upper half, with two exceptions: 0xD7 is OE (not multiply) and
#: 0xF7 is oe (not divide). Getting those two wrong turns `ô` into a division sign.
_T1_HIGH_EXCEPTIONS = {0xD7: 'Œ', 0xDD: 'Ý', 0xF7: 'œ', 0xFD: 'ý'}


def _build_t1() -> dict[int, str]:
    table: dict[int, str] = {}
    table.update(COMBINING)
    table.update(_T1_LOW)
    for code in range(0x20, 0x7F):
        table[code] = chr(code)
    table[0x22] = '”'      # T1 puts a right quote where ASCII has a dumb quote
    table[0x27] = '’'
    table[0x60] = '‘'
    table[0x7F] = '-'           # soft hyphen, the one that ends a hyphenated line
    table.update(_T1_CE)
    for code in range(0xC0, 0x100):
        table[code] = bytes([code]).decode('latin-1')
    table.update(_T1_HIGH_EXCEPTIONS)
    return table


T1 = _build_t1()

# --- OT1 ---------------------------------------------------------------------
#
# The `cm` text fonts. ASCII-ish, and with no accented letters at all -- which is why a
# booklet set in `cmr` rather than `dcr` has to compose every diacritic from a separate mark.

_OT1_LOW = {
    0x0B: 'ff', 0x0C: 'fi', 0x0D: 'fl', 0x0E: 'ffi', 0x0F: 'ffl',
    0x10: 'ı', 0x11: 'ȷ',
    0x12: '̀', 0x13: '́', 0x14: '̌', 0x15: '̆', 0x16: '̄',
    0x17: '̊', 0x18: '̧', 0x19: 'ß', 0x1A: 'æ', 0x1B: 'œ',
    0x1C: 'ø', 0x1D: 'Æ', 0x1E: 'Œ', 0x1F: 'Ø',
}


def _build_ot1() -> dict[int, str]:
    table = dict(_OT1_LOW)
    for code in range(0x20, 0x7F):
        table[code] = chr(code)
    table[0x22] = '”'
    table[0x27] = '’'
    table[0x3C] = '¡'      # OT1 has inverted punctuation where ASCII has < >
    table[0x3E] = '¿'
    table[0x5C] = '“'
    table[0x5E] = '̂'
    table[0x5F] = '̇'
    table[0x60] = '‘'
    table[0x7B] = '–'
    table[0x7C] = '—'
    table[0x7D] = '̋'
    table[0x7E] = '̃'
    table[0x7F] = '̈'
    return table


OT1 = _build_ot1()

# --- TeX math italic (cmmi) --------------------------------------------------
#
# Latin letters sit at their ASCII positions, but the *lower-case Greek alphabet occupies
# 0x0B-0x1F* and the upper case 0x00-0x0A. A booklet's `\alpha` is therefore byte 0x0B in
# `cmmi`, and reading it with a text table yields a control character -- which is exactly
# what `pdftotext` does, and why Greek disappears from its output.

MATH_ITALIC = {
    0x00: r'\Gamma', 0x01: r'\Delta', 0x02: r'\Theta', 0x03: r'\Lambda', 0x04: r'\Xi',
    0x05: r'\Pi', 0x06: r'\Sigma', 0x07: r'\Upsilon', 0x08: r'\Phi', 0x09: r'\Psi',
    0x0A: r'\Omega',
    0x0B: r'\alpha', 0x0C: r'\beta', 0x0D: r'\gamma', 0x0E: r'\delta', 0x0F: r'\epsilon',
    0x10: r'\zeta', 0x11: r'\eta', 0x12: r'\theta', 0x13: r'\iota', 0x14: r'\kappa',
    0x15: r'\lambda', 0x16: r'\mu', 0x17: r'\nu', 0x18: r'\xi', 0x19: r'\pi',
    0x1A: r'\rho', 0x1B: r'\sigma', 0x1C: r'\tau', 0x1D: r'\upsilon', 0x1E: r'\phi',
    0x1F: r'\chi', 0x20: r'\psi', 0x21: r'\omega',
    0x22: r'\varepsilon', 0x23: r'\vartheta', 0x24: r'\varpi', 0x25: r'\varrho',
    0x26: r'\varsigma', 0x27: r'\varphi',
    0x28: r'\leftharpoonup', 0x29: r'\leftharpoondown',
    0x2A: r'\rightharpoonup', 0x2B: r'\rightharpoondown',
    0x2C: r'\lfloor', 0x2D: r'\rfloor', 0x2E: r'\lceil', 0x2F: r'\rceil',
    0x3A: '.', 0x3B: ',', 0x3C: '<', 0x3D: '/', 0x3E: '>', 0x3F: r'\star',
    0x40: r'\partial', 0x5C: r'\natural', 0x5E: r'\smile', 0x5F: r'\frown',
    0x60: r'\ell', 0x7B: r'\imath', 0x7C: r'\jmath', 0x7D: r'\wp',
}
for _c in range(0x30, 0x3A):
    MATH_ITALIC.setdefault(_c, chr(_c))
for _c in list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)):
    MATH_ITALIC.setdefault(_c, chr(_c))

# --- TeX math symbols (cmsy) -------------------------------------------------
#
# **This is where the minus sign lives**, at 0x00. Every "the minus signs simply vanish"
# observation about these booklets is this one table being absent.

MATH_SYMBOL = {
    0x00: '-', 0x01: r'\cdot', 0x02: r'\times', 0x03: '*', 0x04: r'\div', 0x05: r'\diamond',
    0x06: r'\pm', 0x07: r'\mp', 0x08: r'\oplus', 0x09: r'\ominus', 0x0A: r'\otimes',
    0x0B: r'\oslash', 0x0C: r'\odot', 0x0D: r'\bigcirc', 0x0E: r'\circ', 0x0F: r'\bullet',
    0x10: r'\asymp', 0x11: r'\equiv', 0x12: r'\subseteq', 0x13: r'\supseteq',
    0x14: r'\leq', 0x15: r'\geq', 0x16: r'\preceq', 0x17: r'\succeq', 0x18: r'\sim',
    0x19: r'\approx', 0x1A: r'\subset', 0x1B: r'\supset', 0x1C: r'\ll', 0x1D: r'\gg',
    0x1E: r'\prec', 0x1F: r'\succ',
    0x20: r'\leftarrow', 0x21: r'\rightarrow', 0x22: r'\uparrow', 0x23: r'\downarrow',
    0x24: r'\leftrightarrow', 0x25: r'\nearrow', 0x26: r'\searrow', 0x27: r'\simeq',
    0x28: r'\Leftarrow', 0x29: r'\Rightarrow', 0x2A: r'\Uparrow', 0x2B: r'\Downarrow',
    0x2C: r'\Leftrightarrow', 0x2D: r'\nwarrow', 0x2E: r'\swarrow', 0x2F: r'\propto',
    0x30: r'\prime', 0x31: r'\infty', 0x32: r'\in', 0x33: r'\ni',
    0x34: r'\triangle', 0x35: r'\bigtriangledown', 0x36: '/', 0x37: r'\forall',
    0x38: r'\exists', 0x39: r'\neg', 0x3A: r'\emptyset', 0x3B: r'\Re', 0x3C: r'\Im',
    0x3D: r'\top', 0x3E: r'\bot', 0x3F: r'\aleph',
    0x5B: r'\cup', 0x5C: r'\cap', 0x5D: r'\uplus', 0x5E: r'\wedge', 0x5F: r'\vee',
    0x60: r'\vdash', 0x61: r'\dashv', 0x62: r'\lfloor', 0x63: r'\rfloor',
    0x64: r'\lceil', 0x65: r'\rceil', 0x66: r'\{', 0x67: r'\}',
    0x68: r'\langle', 0x69: r'\rangle', 0x6A: '|', 0x6B: r'\|',
    0x6C: r'\updownarrow', 0x6D: r'\Updownarrow', 0x6E: r'\setminus', 0x6F: r'\wr',
    0x70: r'\sqrt', 0x71: r'\amalg', 0x72: r'\nabla', 0x73: r'\smallint',
    0x78: r'\dagger', 0x79: r'\ddagger', 0x7A: r'\|', 0x7B: r'\angle',
}
for _c in range(0x41, 0x5B):
    MATH_SYMBOL.setdefault(_c, rf'\mathcal{{{chr(_c)}}}')

#: Every table, by the name `classify` returns.
TABLES = {
    't1': T1,
    'ot1': OT1,
    'math-italic': MATH_ITALIC,
    'math-symbol': MATH_SYMBOL,
}

#: Fonts whose role is mathematical: a run in one of these opens `$…$`.
MATH_ROLES = {'math-italic', 'math-symbol', 'math-extension', 'ams'}


def classify(font: str) -> tuple[str, str]:
    """
    (role, style) for a PDF font name.

    The name arrives subsetted and decorated -- `ILLJBL+dcti100450957` -- so the stem is what
    matters. Returns the table name and whether the face is upright, italic or bold, because
    the style is not decoration here: upright inside maths is how these booklets write a
    unit, which is what `rules.spaced_units` keys on.
    """
    stem = font.split('+')[-1].lower().lstrip('0123456789')
    for prefix, role in (
        ('dcbx', 't1'), ('dcti', 't1'), ('dcsl', 't1'), ('dcr', 't1'), ('dc', 't1'),
        ('cmmi', 'math-italic'),
        ('cmsy', 'math-symbol'),
        ('cmex', 'math-extension'),
        ('msam', 'ams'), ('msbm', 'ams'),
        ('cmbx', 'ot1'), ('cmti', 'ot1'), ('cmsl', 'ot1'), ('cmtt', 'ot1'), ('cmr', 'ot1'),
        ('csbx', 'ot1'), ('csti', 'ot1'), ('csr', 'ot1'),
        ('symbol', 'symbol'), ('math1', 'symbol'),
    ):
        if stem.startswith(prefix):
            style = ('bold' if 'bx' in prefix else
                     'italic' if 'ti' in prefix or prefix == 'cmmi' else
                     'upright')
            return role, style
    return 'unknown', 'upright'


def decode(code: int, role: str) -> str | None:
    """
    One character code in one font's encoding, or None if the table does not cover it.

    None is a finding, not a failure: `draft.py` reports every uncovered (role, code) pair
    so the table grows by evidence rather than by guesswork, exactly as `units.py` does.
    """
    table = TABLES.get(role)
    if table is None:
        return None
    return table.get(code)
