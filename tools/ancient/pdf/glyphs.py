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
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from tools.ancient.pdf import encodings

RE_SPAN = re.compile(r'<span font="([^"]*)"[^>]*trm="([^"]*)"')
RE_GLYPH = re.compile(r'<g unicode="([^"]*)" glyph="([^"]*)" x="([-\d.]+)" y="([-\d.]+)" adv="([-\d.]+)"')
RE_GNAME = re.compile(r'^G?(\d+)$')

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


def _numbers(raw: str) -> list[tuple[str, int | None, str, float, float, float, float]]:
    """
    (font, glyph number or None, mupdf's unicode, x, y, adv, size) in drawing order.

    Both channels are carried because which one to believe depends on the font: see
    `_character`. A glyph whose name is not a number keeps `None` and must fall back to the
    unicode, which is the case for 10.pdf, where the names are real (`one`, `period`, `Z`).
    """
    out = []
    font, size = '', 10.0
    for line in raw.splitlines():
        if (m := RE_SPAN.search(line)):
            font = m.group(1)
            try:
                size = abs(float(m.group(2).split()[0]))
            except (ValueError, IndexError):
                size = 10.0
        for g in RE_GLYPH.finditer(line):
            uni, name, x, y, adv = g.groups()
            n = RE_GNAME.match(name)
            out.append((font, int(n.group(1)) if n else None, uni,
                        float(x), float(y), float(adv), size))
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
    if uni and uni != REPLACEMENT:
        return uni, shifted if shifted is not None else ord(uni)
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


@functools.cache
def identified(volume: str) -> dict[str, dict[int, str]]:
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
    return yaml.safe_load(path.read_text()) or {}


def _family(font: str) -> str:
    """`ILLJBL+cmmi120450` -> `cmmi`. The size is dropped: cmr8 and cmr12 share a numbering."""
    stem = font.split('+')[-1].lower().lstrip('0123456789')
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

    table = identified(volume) if volume else {}
    glyphs = []
    for font, n, uni, x, y, adv, size in _numbers(raw):
        role, style = encodings.classify(font)
        # A read identification beats every table: it is what the glyph looks like, not what
        # an encoding says the code ought to mean.
        ch = table.get(_family(font), {}).get(n) if n is not None else None
        sure = ch is not None or role in ('t1', 'ot1') and not table
        code = n if n is not None else 0
        if ch is None:
            ch, code = _character(n, uni, role, shift)
            sure = sure or role == 't1' or (uni not in ('', REPLACEMENT))
        if ch is None:
            continue
        glyphs.append(Glyph(ch, x, y, adv * size, size, role, style, code, sure))

    boxes = []
    kind, pts = None, []
    for line in raw.splitlines():
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
                a, _b, _c, d, e, f = (float(v) for v in parts[:6])
                top, bottom = f, f + abs(d)
                boxes.append(Box('image', e, height - bottom, e + abs(a), height - top))
            except ValueError:
                pass
        for p in RE_POINT.finditer(line):
            pts.append((float(p.group(1)), float(p.group(2))))
    if kind and pts:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        boxes.append(Box(kind, min(xs), min(ys), max(xs), max(ys)))

    return glyphs, boxes, shift
