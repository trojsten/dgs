"""
Reading a booklet's glyph stream out of the PDF.

`mutool draw -F trace` is the substrate rather than `pdftotext`, because it keeps the three
things the decode needs and `pdftotext` throws away:

- **the font of every glyph**, which names its encoding (see `encodings.classify`);
- **the position of every glyph**, without which the accents cannot be reattached, the
  columns cannot be split and the fraction bars cannot be found;
- **the image masks and the paths**, which are the `ý` bitmap and the drawings.

Subset fonts name their glyphs `G<n>`, and mupdf reports that name verbatim. For these
booklets the true character code is `n` minus a small constant -- 3, in every file that has
one. The constant is *fitted per file* by `fit_shift` rather than assumed, because a wrong
shift produces nonsense Slovak and so announces itself, and because 09 has no shift at all.
"""

from __future__ import annotations

import functools
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from tools.ancient.pdf import encodings, metrics

RE_SPAN = re.compile(r'<span font="([^"]*)"[^>]*trm="([^"]*)"')
RE_TEXTBLOCK = re.compile(r'<fill_text[^>]*transform="([^"]*)"')
RE_GLYPH = re.compile(r'<g unicode="([^"]*)" glyph="([^"]*)" x="([-\d.]+)" y="([-\d.]+)" adv="([-\d.]+)"')
#: A subset glyph's name. `G46` is character code 46 -- and `G46._` is a *second* glyph that
#: the embedded CFF charset also calls `G46`, which mupdf disambiguates with the suffix. Two
#: of these booklets are two documents merged, so a name can collide, and where it does the
#: two glyphs are unrelated: in `04.pdf`'s `cmr` the plain `G46` is `\doteq` and the duplicate
#: is the digit **7**. Left unmatched the duplicate decoded to nothing and was dropped without
#: a word -- `400/27` printed as `400/2` -- so it is numbered separately, as the negative of
#: the name it collides with, and a table names it like any other glyph.
RE_GNAME = re.compile(r'^G?(\d+)(\._)?$')

#: mupdf's trace is XML, so the `unicode` attribute is escaped -- and the five characters it
#: escapes are all ones these booklets use. Read raw, `R>r` arrived as `R&gt;r`, which reaches
#: the TeX as a literal `&` and stops the build with `Misplaced alignment tab character &`;
#: `"` came through as `&quot;` in the middle of a Slovak sentence. Only the booklets whose
#: fonts mupdf can resolve are affected, which is 09 and 11.
#:
#: The five by name rather than `html.unescape`, which also decodes named entities without
#: their semicolon and would turn a literal `&amp` in a formula into something else.
XML_ENTITIES = {'&lt;': '<', '&gt;': '>', '&quot;': '"', '&apos;': "'", '&amp;': '&'}

RE_ENTITY = re.compile('|'.join(XML_ENTITIES))


def _unescape(text: str) -> str:
    """`&gt;` -> `>`, in one pass, so an escaped entity is not decoded twice."""
    return RE_ENTITY.sub(lambda m: XML_ENTITIES[m.group(0)], text)


#: mupdf writes this when the font gives it nothing to work with -- which is the normal case
#: for 02-08, and the signal to decode from the glyph name instead.
REPLACEMENT = '�'
RE_IMAGE = re.compile(r'<fill_image_mask[^>]*transform="([^"]*)"')
RE_PATHOPEN = re.compile(r'<(fill_path|stroke_path)\b')
RE_POINT = re.compile(r'<(?:moveto|lineto) x="([-\d.]+)" y="([-\d.]+)"')
RE_MEDIABOX = re.compile(r'<page mediabox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"')

#: Letters that are common in Slovak and rare as noise. Scoring a candidate shift on these
#: is enough to separate the right one from all 255 others by a wide margin.
SLOVAK_COMMON = set('aeiounrstvklmpdjczbhýáíéúšžčťľô ')


@dataclass(frozen=True)
class Glyph:
    """One drawn character: what it is, where it is, and which font drew it."""
    char: str
    x: float
    y: float
    adv: float
    size: float
    role: str
    style: str
    code: int
    #: True when this character was *identified* -- read off a contact sheet, or decoded from
    #: a font whose glyph names really are character codes. False means a table's best guess,
    #: which for these subset maths fonts is not worth printing.
    sure: bool = True
    #: '', 'sup' or 'sub'. A raised or lowered baseline is the only record a PDF keeps of an
    #: exponent: there is no markup, just a smaller glyph placed higher up.
    script: str = ''

    @property
    def combining(self) -> bool:
        return self.char in encodings.COMBINING.values()

    @property
    def maths(self) -> bool:
        return self.role in encodings.MATH_ROLES


@dataclass(frozen=True)
class Box:
    """A drawn path or an image mask, as its bounding box."""
    kind: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def rule(self) -> bool:
        """
        A rule is thin and wide: a header line, a fraction bar, a table rule.

        Worth naming because it cuts both ways -- these must be excluded before clustering
        paths into figures, and a *short* one sitting between two runs of maths is a
        fraction bar, which is the only surviving trace of a fraction's structure.
        """
        return self.height < 1.2 and self.width > 4 * max(self.height, 0.01)


def trace(pdf: Path, page: int) -> str:
    """The raw trace for one page. Pages are 1-based, as mutool counts them."""
    return subprocess.run(
        ['mutool', 'draw', '-F', 'trace', '-o', '-', str(pdf), str(page)],
        capture_output=True, text=True, check=True).stdout


def page_rotated(raw: str) -> bool:
    """Is this page's text turned on its side? True when most spans say so."""
    turned = upright = 0
    for m in RE_SPAN.finditer(raw):
        try:
            a, b = (abs(float(v)) for v in m.group(2).split()[:2])
        except ValueError:
            continue
        if b > a:
            turned += 1
        else:
            upright += 1
    return turned > upright


def _numbers(raw: str) -> list[tuple[str, int | None, str, float, float, float, float]]:
    """
    (font, glyph number or None, mupdf's unicode, x, y, adv, size) in drawing order.

    Both channels are carried because which one to believe depends on the font: see
    `_character`. A glyph whose name is not a number keeps `None` and must fall back to the
    unicode, which is the case for 10.pdf, where the names are real (`one`, `period`, `Z`).
    """
    out = []
    font, size, rotated = '', 10.0, False
    # The current transformation matrix of the text block. **Each block carries its own**, and
    # on an imposed sheet the two columns are two blocks with different ones -- so ignoring it
    # laid volume 05's two logical pages exactly on top of each other, which is why its folios
    # read as one page and its gutter could not be found. It also carries the A4-to-A5
    # reduction these booklets are printed at.
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for line in raw.splitlines():
        if (mb := RE_TEXTBLOCK.search(line)):
            try:
                ctm = tuple(float(v) for v in mb.group(1).split()[:6])
            except ValueError:
                ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        if (m := RE_SPAN.search(line)):
            font = m.group(1)
            # The text matrix is `a b c d`. Upright text has the size in `a`; text turned on
            # its side has `a = 0` and the size in `b`, which is why volume 02 -- printed two
            # up and rotated ninety degrees -- came out with every glyph at size zero and
            # every line a single character.
            try:
                a, b = (abs(float(v)) for v in m.group(2).split()[:2])
                size = max(a, b) or 10.0
                rotated = b > a
            except (ValueError, IndexError):
                size, rotated = 10.0, False
        for g in RE_GLYPH.finditer(line):
            uni, name, x, y, adv = g.groups()
            uni = _unescape(uni)
            n = RE_GNAME.match(name)
            a, b, c, d, e, f = ctm
            gx0, gy0 = float(x), float(y)
            # Into device space, then negate y so that larger still means higher up, which is
            # what the line clustering assumes.
            gx = a * gx0 + c * gy0 + e
            gy = -(b * gx0 + d * gy0 + f)
            scale = abs(a * d - b * c) ** 0.5 or 1.0
            gsize = size * scale
            if rotated:
                # Rotated text runs up the page at constant x, so lines share an *x* and
                # advance in *y*. Mapped here into the one space everything downstream
                # assumes: a line shares a baseline and advances rightwards.
                gx, gy = gy, -gx
            number = None if n is None else int(n.group(1))
            if n is not None and n.group(2):
                # Zero is the only code whose negative is itself, and `cmsy`'s `G0` is the
                # minus sign, so a `G0._` would alias onto it in silence. Nothing in these
                # eleven booklets has one -- `G46._` is the only duplicate in the corpus --
                # and if one ever turns up it should say so rather than decode as a minus.
                if number == 0:
                    raise ValueError(f'{font}: a duplicate G0 cannot be numbered as -0')
                number = -number
            out.append((font, number, uni, gx, gy, float(adv), gsize))
    return out


def _character(code: int | None, uni: str, role: str, shift: int) -> tuple[str | None, int]:
    """
    One glyph's character, and the code it was read at.

    **Maths prefers the table, text prefers mupdf.** Inside `cmmi` or `cmsy` the table is the
    only thing that yields `\\alpha` and `\\cdot` rather than a bare Greek letter or nothing at
    all -- and it is the only thing that yields the minus sign, which lives at `cmsy` 0x00.
    Outside maths, a `unicode` mupdf actually resolved is better evidence than any table,
    because the font told it so; that is what makes 09 and 10 work unchanged.
    """
    shifted = None if code is None else code - shift
    if role in encodings.MATH_ROLES and shifted is not None:
        if (ch := encodings.decode(shifted, role)) is not None:
            return ch, shifted
    uni = encodings.unligate(uni)
    if uni and uni != REPLACEMENT:
        # A ligature resolves to more than one character -- `ffi` is one glyph and three
        # code points -- so there is no single code to report for it. `11.pdf` is the first
        # booklet whose fonts are named well enough for mupdf to resolve those at all.
        code_point = ord(uni) if len(uni) == 1 else 0
        return uni, shifted if shifted is not None else code_point
    if shifted is None:
        return None, 0
    return encodings.decode(shifted, role), shifted


def fit_shift(raw: str) -> int:
    """
    The constant to subtract from every G-number, measured rather than assumed.

    Scored on how much ordinary Slovak the text fonts produce. The right shift wins by a
    wide margin; if it does not, the caller should stop rather than proceed, because a
    near-tie means this file is not encoded the way the others are.
    """
    text = [(f, n) for f, n, uni, *_ in _numbers(raw)
            if n is not None and uni in ('', REPLACEMENT)
            and encodings.classify(f)[0] in ('t1', 'ot1')]
    if not text:
        return 0        # nothing is mis-encoded here; 09 and 10 land on this line
    best, best_score = 0, -1.0
    for shift in range(8):
        hits = 0
        for font, n in text:
            role = encodings.classify(font)[0]
            ch = encodings.decode(n - shift, role)
            if ch and ch.lower() in SLOVAK_COMMON:
                hits += 1
        score = hits / len(text)
        if score > best_score:
            best, best_score = shift, score
    return best


class WrongBookletError(Exception):
    """A glyph table read from one booklet, handed to another."""


@functools.cache
def identified(volume: str, fingerprint: str | None = None) -> dict[str, dict[int, str]]:
    """
    The glyphs a person has read off a contact sheet, for one booklet.

    This is the authority wherever it has an entry. The standard encodings can only decode a
    font whose glyph names are character codes, and in these booklets `cmr` is a merged
    subset whose numbering is arbitrary -- so for maths there is no table to look up, only a
    table to *write*, once, from `sheet.py`'s montage. `tools/ancient/glyphs/2007.yaml` did
    the same for that year's figures.
    """
    path = Path(__file__).parent / 'glyphs' / f'{volume}.yaml'
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    declared = data.pop('source-md5', None)
    data['_trust'] = set(data.pop('trust', []) or [])
    # A table is only valid for the file it was read from. Each booklet is subset separately,
    # so the same G-number means different characters in different years -- and a table
    # applied to the wrong file does not fail, it silently returns confident wrong letters.
    # That is the one failure mode worth an exception rather than a warning.
    if declared and fingerprint and declared != fingerprint:
        raise WrongBookletError(
            f'{path.name} was read from a booklet with md5 {declared}, but this one is '
            f'{fingerprint}. Glyph numbering is per subset; run `sheet.py` for this file.')
    return data


@functools.lru_cache(maxsize=None)
def prose_roles(pdf: Path) -> frozenset[str]:
    """
    Which font roles carry this booklet's *prose*, as opposed to its formulas.

    For nine of the ten booklets the answer is `t1` and nothing else: prose is set in `dcr`
    (T1/Cork, which is what gives Slovak its accented letters in one byte) and `cmr` is the
    upright roman *inside* maths -- the digits of a quantity, the `d` of a differential. A
    `cmr` run is therefore a formula, and that is what tells `_text` where a formula begins.

    **`11.pdf` has no T1 font at all.** It is the one booklet set in CSfonts -- `csr12`,
    `csbx12`, `csti12`, the Czech/Slovak cut of Computer Modern -- with real glyph names and
    WinAnsi encoding, and its prose is `csr`, which classifies as `ot1` like `cmr`. Read with
    the usual rule every line of it came out as one enormous formula, correctly spelled and
    entirely unusable: `$1.KamiónsavydalzmestaAdomestaB$`.

    So it is measured rather than assumed, from the fonts the file actually embeds. A booklet
    with a T1 font keeps the narrow rule; one without admits `ot1` as prose too.
    """
    info = subprocess.run(['mutool', 'info', '-F', str(pdf)], capture_output=True, text=True).stdout
    roles = {encodings.classify(m)[0] for m in re.findall(r"'([^']+)'", info)}
    return frozenset({'t1'}) if 't1' in roles else frozenset({'t1', 'ot1'})


@functools.lru_cache(maxsize=None)
def _widths(pdf: Path) -> dict[str, dict[int, list[int]]]:
    """`metrics.candidates`, once per booklet rather than once per page."""
    try:
        return metrics.candidates(pdf)
    except Exception:
        # A booklet whose fonts carry no usable metric -- 09 and 10, whose fonts are TrueType
        # and CID -- must still convert. The other channels have always been enough there.
        return {}


@functools.lru_cache(maxsize=None)
def _fingerprint(pdf: Path) -> str:
    """The booklet's md5, which is what a glyph table is valid for."""
    return hashlib.md5(Path(pdf).read_bytes()).hexdigest()


def _stem(font: str) -> str:
    """`ILLJBL+cmr120450` -> `cmr1204`. The subset prefix goes; nothing else does."""
    return font.split('+')[-1].lower()


def _family(font: str) -> str:
    """
    `ILLJBL+cmmi120450` -> `cmmi`. The size is dropped, because one booklet's `cmr8` and
    `cmr12` are normally cut from one merged subset and share a numbering.

    **Normally, not always.** `02.pdf` carries two independent `cmr` subsets: `cmr1003`,
    `cmr7026` and `cmr5019` are plain OT1 shifted by three, while `cmr1204`, `cmr8030` and
    `cmr6023` are the scrambled merge that 03, 04 and 05 also use -- so in that booklet G51
    is `0` in one and `(` in the other. A table keyed on the family alone would hand the
    scramble to the plain subset and produce a page of confident wrong letters, which is the
    one failure these tables exist to prevent. Hence `read_page` looks the stem up first and
    only falls back here, and `glyphs/02.yaml` is keyed by stem.
    """
    stem = _stem(font).lstrip('0123456789')
    return re.match(r'^[a-z]+', stem).group(0) if re.match(r'^[a-z]+', stem) else stem


def read_page(pdf: Path, page: int, shift: int | None = None,
              volume: str | None = None) -> tuple[list[Glyph], list[Box], int]:
    """
    Every glyph and every box on one page, decoded.

    `shift` is fitted from this page when not given. Returns it too, so a caller converting a
    whole booklet can fit once and reuse -- and so the report can state what was measured.
    """
    raw = trace(pdf, page)
    if shift is None:
        shift = fit_shift(raw)
    mb = RE_MEDIABOX.search(raw)
    height = float(mb.group(4)) if mb else 842.0

    table = identified(volume, _fingerprint(pdf)) if volume else {}
    # The second channel. `metrics` reads each subset font's own `/Widths` against the TeX
    # metric it names, which identifies a glyph without anyone looking at it -- see that
    # module for why it is worth having beside the hand-read tables rather than instead of
    # them. It is consulted only where the table is silent.
    widths = _widths(pdf)
    glyphs = []
    for font, n, uni, x, y, adv, size in _numbers(raw):
        role, style = encodings.classify(font)
        if role == 'drawing':
            continue                # a bitmap tile inside a figure -- see `encodings.classify`
        # A read identification beats every table: it is what the glyph looks like, not what
        # an encoding says the code ought to mean.
        family, stem = _family(font), _stem(font)
        # The stem wins where a booklet names one: see `_family` for the booklet that needs it.
        entries = table.get(stem) or table.get(family) or {}
        ch = entries.get(n) if n is not None else None
        # A family listed under `trust:` decodes by its standard table rather than by reading.
        # `cmmi` earns that in every booklet checked so far -- its Greek sits exactly three
        # above its own code points, which is a proof the sheet only confirms -- while `cmr`
        # is a merged subset and is scrambled, so it is never trusted.
        trusted = table.get('_trust', ())
        sure = (ch is not None or family in trusted or stem in trusted
                or (role in ('t1', 'ot1') and not table))
        code = n if n is not None else 0
        if ch is None and n is not None:
            if len(found := widths.get(stem, {}).get(n, ())) == 1:
                ch, code = encodings.decode(found[0], role), found[0]
                sure = sure or ch is not None
        if ch is None:
            ch, code = _character(n, uni, role, shift)
            sure = sure or role == 't1' or (uni not in ('', REPLACEMENT))
        if ch is None:
            continue
        glyphs.append(Glyph(ch, x, y, adv * size, size, role, style, code, sure))

    boxes = []
    kind, pts = None, []
    turned = page_rotated(raw)
    pctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for line in raw.splitlines():
        if (mt := re.search(r'transform="([^"]*)"', line)) and ('path' in line or 'image' in line):
            try:
                pctm = tuple(float(v) for v in mt.group(1).split()[:6])
            except ValueError:
                pctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        if (m := RE_PATHOPEN.search(line)):
            if kind and pts:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                boxes.append(Box(kind, min(xs), min(ys), max(xs), max(ys)))
            kind, pts = m.group(1), []
        elif RE_IMAGE.search(line):
            # The `ý` bitmap. Its CTM is `a b c d e f`: e, f place it and a, d scale it.
            #
            # Unlike the paths, this translation is in *device* space, where y runs the other
            # way -- so it is flipped here, at the one place that knows the page height, and
            # every caller downstream sees a single coordinate space. Left unflipped, the
            # bitmaps land 600 points from the line they belong to and splice into whatever
            # happens to be nearest.
            parts = RE_IMAGE.search(line).group(1).split()
            try:
                a, ib, ic, d, e, f = (float(v) for v in parts[:6])
                # The CTM maps the unit square onto the placement, so the box is the transform
                # of its four corners -- not `|a|` by `|d|`, which is zero for a rotated
                # placement, and not the column lengths either, which give the right numbers
                # the wrong way round and then get rotated a second time.
                corners = [(a * u + ic * v + e, ib * u + d * v + f)
                           for u, v in ((0, 0), (1, 0), (0, 1), (1, 1))]
                cxs = [c[0] for c in corners]
                cys = [c[1] for c in corners]
                # Same space as the glyphs: device coordinates with y negated, so that
                # `larger` still means `higher up`. Matching a bitmap to its line is the whole
                # point, and the two have to be measured the same way.
                bx0, by0, bx1, by1 = min(cxs), -max(cys), max(cxs), -min(cys)
                if turned:
                    # The glyphs were mapped out of the rotated space; a bitmap sitting among
                    # them has to make the same journey or it lands a page away from its word.
                    bx0, by0, bx1, by1 = by0, -bx1, by1, -bx0
                boxes.append(Box('image', bx0, by0, bx1, by1))
            except ValueError:
                pass
        for p in RE_POINT.finditer(line):
            pa, pb, pc, pd, pe, pf = pctm
            px, py = float(p.group(1)), float(p.group(2))
            tx, ty = pa * px + pc * py + pe, -(pb * px + pd * py + pf)
            pts.append((ty, -tx) if turned else (tx, ty))
    if kind and pts:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        boxes.append(Box(kind, min(xs), min(ys), max(xs), max(ys)))

    return glyphs, boxes, shift
