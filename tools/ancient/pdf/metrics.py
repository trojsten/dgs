r"""
Identifying a subset font's glyphs from its own width table.

The problem these booklets pose is that a subset font names its glyphs `G<n>` where `n` is
meaningless -- `sheet.py` exists because of it, and every `glyphs/NN.yaml` in this directory
was read off a contact sheet by eye. That works, and it is slow, and a misread glyph is
silent.

There is a better source, and it is inside the file. A Type1 font dictionary carries

- **`/BaseFont`**, which for these is `DHADDN+cmmi120462` -- and `cmmi12` is a font whose
  metrics ship with every TeX installation;
- **`/Differences`**, mapping each character code actually used to one of those `G<n>` names;
- **`/Widths`**, the advance of each of those codes, in thousandths of an em.

So the width of `G54` is known, and `cmmi12.tfm` says which characters have that width. Where
exactly one does, the glyph is **identified**, with no eye involved and no table to maintain.
In `02.pdf`'s `cmmi120462` that settles 33 of 43 outright, and it settles them *correctly*:
read by eye off a 600 dpi crop, `G79` looked like a second italic `B`, which is impossible --
it is the `\vec` accent, and the `B` underneath it was simply inside the crop.

Ambiguity is real and is reported rather than resolved: in `cmmi12` the oldstyle digits all
share one width, as do `R` and `B`. A caller falls back to the hand-read table for those, so
the two channels compose -- metrics first, because it cannot misread, then the sheet for what
metrics cannot split.

**The font must prove itself.** A name is not evidence, so the widths are scored against the
metric before it is believed: `cmmi120462` matches `cmmi12` on 42 of its 43 widths and the
next best candidate manages 21. Below `THRESHOLD` the font is left to the other channels.
"""

from __future__ import annotations

import functools
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

#: `DHADDN+cmmi120462` -> family `cmmi`, design size `12`. The trailing four digits are the
#: scale dvips baked into the name (12 x 38.5 = 462 here, 10 x 46.2 = 462 for the other stream
#: in the same file), so the design size is whatever is left once they are taken off.
RE_BASEFONT = re.compile(r'^(?:[A-Z]{6}\+)?([A-Za-z]+)(\d+)$')

#: `(CHARACTER C x` or `(CHARACTER O 176`, then the width on the next line.
RE_CHARWD = re.compile(r'\(CHARACTER (?:(C) (\S)|O (\d+))\s*\n\s*\(CHARWD R ([\d.]+)\)')

#: A font object, as `mutool show <pdf> grep` prints it -- one per line.
RE_FONT = re.compile(r'^(\d+) 0 obj <<(.*/BaseFont/[^/>]+.*)>>$')
RE_ENCODING_REF = re.compile(r'/Encoding (\d+) 0 R')
RE_DIFFERENCES = re.compile(r'/Differences\s*\[([^\]]*)\]')
#: The array's entries. `mutool show ... grep` prints it packed -- `[1/G42/G54/...]` -- while
#: `mutool show ... <n>` spaces it out, so splitting on whitespace finds one token in the one
#: case and forty-four in the other. Matching the shapes is what works on both.
RE_DIFF_TOKEN = re.compile(r'/([A-Za-z0-9._]+)|(\d+)')
RE_WIDTHS = re.compile(r'/Widths\s*\[([^\]]*)\]')
RE_FIRSTCHAR = re.compile(r'/FirstChar (\d+)')

#: The fraction of a font's widths that must exist in the candidate metric before the metric
#: is believed. The real signal is far above this -- 0.98 against 0.49 for the runner-up -- so
#: the margin is not delicate; what the gate is for is a font that ships no metric at all.
THRESHOLD = 0.8

#: Widths are rounded to whole thousandths on both sides, so equality is to within this. Four
#: rather than one, because the slop grows at small design sizes: the minus of `07.pdf`'s
#: `cmsy6` is recorded as 960 against the metric's 963, and at a tolerance of two it came out
#: as `\mathcal{D}` -- a clean, confident, wrong answer of exactly the kind this module is
#: supposed to stop. Four still splits every character `cmr12` and `cmsy10` have.
TOLERANCE = 4


@functools.lru_cache(maxsize=None)
def tfm(name: str) -> dict[int, int]:
    """Every character of a TeX font metric, as code -> width in thousandths of an em."""
    path = subprocess.run(['kpsewhich', f'{name}.tfm'],
                          capture_output=True, text=True).stdout.strip()
    if not path:
        return {}
    pl = subprocess.run(['tftopl', path], capture_output=True, text=True).stdout
    out = {}
    for m in RE_CHARWD.finditer(pl):
        code = ord(m.group(2)) if m.group(1) else int(m.group(3), 8)
        out[code] = round(float(m.group(4)) * 1000)
    return out


def _metric_for(basefont: str) -> Iterator[tuple[str, dict[int, int]]]:
    """
    The TeX metric a `/BaseFont` name refers to, and its widths.

    The design size has to be split off a run of digits that also carries dvips' scale, and
    the split is not decidable from the string -- `cmr100385` could be `cmr10` or `cmr1`. So
    every split that names a metric on this machine is a candidate, and the caller scores
    them against the actual widths; this only has to offer them.
    """
    m = RE_BASEFONT.match(basefont)
    if not m:
        return
    family, digits = m.group(1), m.group(2)
    for cut in range(1, len(digits)):
        name = f'{family}{digits[:cut]}'
        if (widths := tfm(name)):
            yield name, widths


def _score(widths: list[int], metric: dict[int, int]) -> float:
    if not widths:
        return 0.0
    present = sum(1 for w in widths if any(abs(cw - w) <= TOLERANCE for cw in metric.values()))
    return present / len(widths)


def candidates(pdf: Path) -> dict[str, dict[int, list[int]]]:
    """
    For each subset font in the file, every glyph number's possible character codes.

    A one-element list is an identification. A longer one is a width the metric cannot split,
    and is left for `glyphs/NN.yaml` to settle. A font with no usable metric is simply absent,
    which is what a caller checks rather than an empty mapping meaning "nothing matched".
    """
    raw = subprocess.run(['mutool', 'show', str(pdf), 'grep'],
                         capture_output=True, text=True).stdout
    encodings: dict[int, list[str]] = {}
    for line in raw.splitlines():
        if (mo := re.match(r'^(\d+) 0 obj <<(.*/Differences.*)>>$', line)):
            if (md := RE_DIFFERENCES.search(mo.group(2))):
                encodings[int(mo.group(1))] = RE_DIFF_TOKEN.findall(md.group(1))

    out: dict[str, dict[int, list[int]]] = {}
    for line in raw.splitlines():
        if not (mf := RE_FONT.match(line)):
            continue
        body = mf.group(2)
        base = re.search(r'/BaseFont/([^/>\s]+)', body).group(1)
        stem = base.split('+')[-1].lower()
        if not (mw := RE_WIDTHS.search(body)) or not (me := RE_ENCODING_REF.search(body)):
            continue
        widths = [int(x) for x in mw.group(1).split()]
        tokens = encodings.get(int(me.group(1)))
        if not tokens:
            continue

        # `/Differences` is [code /name /name ... code /name ...]; these files use one run, but
        # the general form costs nothing to honour and a second run would otherwise misalign
        # every width after it.
        by_code: dict[int, str] = {}
        code = int(RE_FIRSTCHAR.search(body).group(1)) if RE_FIRSTCHAR.search(body) else 0
        for name, number in tokens:
            if name:
                by_code[code] = name
                code += 1
            else:
                code = int(number)

        first = int(RE_FIRSTCHAR.search(body).group(1)) if RE_FIRSTCHAR.search(body) else 0
        best, best_score = {}, 0.0
        for _name, metric in _metric_for(base) or ():
            if (s := _score(widths, metric)) > best_score:
                best, best_score = metric, s
        if best_score < THRESHOLD:
            continue

        table: dict[int, list[int]] = {}
        for i, w in enumerate(widths):
            name = by_code.get(first + i)
            if not name or not (mg := re.fullmatch(r'G(\d+)', name)):
                continue
            table[int(mg.group(1))] = sorted(
                c for c, cw in best.items() if abs(cw - w) <= TOLERANCE)
        out[stem] = table
    return out
