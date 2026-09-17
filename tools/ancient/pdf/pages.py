"""
Taking a printed sheet apart into the pages that were printed on it.

Two of these booklets are **imposed**: `05.pdf` puts two logical pages side by side on a
landscape sheet, and `02.pdf` does the same and turns the whole thing ninety degrees. A sheet
like that is not a page, and reading it as one interleaves two columns of prose line by line --
`1. Zadania 3 4`, with the twelfth problem's statement running into the eighteenth's.

Nothing in the file says a sheet is imposed. What says so is the geometry: a band down the
middle that no glyph crosses, and two folios in the running head where there should be one.
Both are measured, and the folios are the check on the measurement -- a sheet whose halves do
not carry two plausible page numbers is reported rather than split on a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tools.ancient.pdf.glyphs import Box, Glyph

#: A folio is a small number sitting alone near the head or foot of a column.
RE_FOLIO = re.compile(r'^\d{1,3}$')


@dataclass
class Half:
    """One logical page lifted off a sheet, and the page number printed on it."""
    folio: int | None
    glyphs: list[Glyph]
    boxes: list[Box]


def gutter(glyphs: list[Glyph]) -> float | None:
    """
    The x of the empty band down the middle of a sheet, or None if there is not one.

    Measured from a histogram of glyph positions rather than assumed to be the centre: these
    sheets are not symmetric, and a split at the midpoint cuts the wider column in half. Only
    the middle of the sheet is considered, because the margins are empty too and are not
    gutters.
    """
    if len(glyphs) < 40:
        return None
    xs = sorted(g.x for g in glyphs)
    lo, hi = xs[0], xs[-1]
    span = hi - lo
    if span <= 0:
        return None

    inner = [x for x in xs if lo + span * 0.3 <= x <= lo + span * 0.7]
    if not inner:
        return (lo + hi) / 2

    # The widest gap between consecutive glyph positions in the middle third.
    best_gap, best_at = 0.0, None
    for a, b in zip(inner, inner[1:]):
        if b - a > best_gap:
            best_gap, best_at = b - a, (a + b) / 2
    # A gutter is wide *relative to the sheet*. A fixed threshold in points fails on a sheet
    # printed at a reduction: one sheet of volume 02 kept its two columns interleaved, and the
    # run of pages after it was lost.
    return best_at if best_gap >= max(12.0, span * 0.025) else None


def _folio(glyphs: list[Glyph]) -> int | None:
    """The page number printed on a column, read off its topmost or bottom-most short line."""
    if not glyphs:
        return None
    rows: dict[float, list[Glyph]] = {}
    for g in glyphs:
        rows.setdefault(round(g.y, 0), []).append(g)
    for y in sorted(rows, reverse=True)[:1] + sorted(rows)[:1]:
        row = sorted(rows[y], key=lambda g: g.x)
        text = ''.join(g.char for g in row).strip()
        if RE_FOLIO.match(text):
            return int(text)
        if (m := re.search(r'(\d{1,3})\s*$', text)) and len(text) < 40:
            return int(m.group(1))
    return None


def split(glyphs: list[Glyph], boxes: list[Box]) -> list[Half]:
    """
    A sheet as the one or two pages printed on it, in the order they are to be read.

    Ordered by folio where both halves carry one, because an imposed sheet is *not* laid out
    left-to-right: saddle-stitching pairs the first page with the last, so `05.pdf`'s first
    sheet carries pages 2 and 34. Reading the halves in the order they sit on the paper would
    interleave the booklet end over end.
    """
    at = gutter(glyphs)
    if at is None:
        return [Half(_folio(glyphs), glyphs, boxes)]

    left = Half(None, [g for g in glyphs if g.x < at], [b for b in boxes if b.x0 < at])
    right = Half(None, [g for g in glyphs if g.x >= at], [b for b in boxes if b.x0 >= at])
    for half in (left, right):
        half.folio = _folio(half.glyphs)

    halves = [h for h in (left, right) if h.glyphs]
    if all(h.folio is not None for h in halves):
        halves.sort(key=lambda h: h.folio)
    return halves
