"""
Glyphs into text.

The decode gives characters and where they sit; this gives lines, words and sentences. Four
things have to happen here that no amount of table-work upstream can do, because each one is
about *position* rather than *identity*:

- **words**, from the gaps between advances -- there are no space characters in the stream;
- **accents**, for the five Slovak letters whose mark is drawn separately (`ď ľ ť ĺ ŕ`);
- **`ý`**, which is not a glyph at all in 02-08 but a bitmap, and arrives as a `Box`;
- **hyphens**, because the booklets are justified and hyphenated, and a line ending in one
  is a word cut in half.

What this deliberately does *not* try to do is reconstruct two-dimensional maths. A fraction
survives only as a rule between two runs; a superscript only as a smaller glyph on a raised
baseline. Those are marked and left for the visual pass, per `%# TODO(math)`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from tools.ancient.pdf import maths
from tools.ancient.pdf.glyphs import Box, Glyph

#: A mark drawn as its own glyph. These booklets set the Slovak apostrophe-caron as a comma
#: or a raised quote rather than reaching for T1's precomposed letter, so the mark arrives
#: beside its letter instead of on it.
MARKS = set(',\'’ˇ´`ʼ') | {
    '̀', '́', '̂', '̃', '̄', '̆', '̇',
    '̈', '̊', '̋', '̌', '̧', '̨',
}

#: What a mark over a letter composes to. Only the combinations Slovak actually uses; a mark
#: landing anywhere else is left alone and reported, rather than guessed into a wrong letter.
COMPOSE = {
    ('d', 'caron'): 'ď', ('l', 'caron'): 'ľ', ('t', 'caron'): 'ť',
    ('D', 'caron'): 'Ď', ('L', 'caron'): 'Ľ', ('T', 'caron'): 'Ť',
    ('l', 'acute'): 'ĺ', ('r', 'acute'): 'ŕ', ('L', 'acute'): 'Ĺ', ('R', 'acute'): 'Ŕ',
    ('a', 'acute'): 'á', ('e', 'acute'): 'é', ('i', 'acute'): 'í', ('o', 'acute'): 'ó',
    ('u', 'acute'): 'ú', ('y', 'acute'): 'ý',
    ('c', 'caron'): 'č', ('s', 'caron'): 'š', ('z', 'caron'): 'ž', ('n', 'caron'): 'ň',
    ('C', 'caron'): 'Č', ('S', 'caron'): 'Š', ('Z', 'caron'): 'Ž',
    ('o', 'circumflex'): 'ô', ('a', 'dieresis'): 'ä',
}

#: A comma-shaped mark riding high is a caron in this typography, not punctuation.
MARK_KIND = {
    ',': 'caron', '’': 'caron', 'ʼ': 'caron', 'ˇ': 'caron', '̌': 'caron',
    "'": 'acute', '´': 'acute', '́': 'acute',
    '`': 'grave', '̀': 'grave',
    '̂': 'circumflex', '̈': 'dieresis', '̃': 'tilde',
}


@dataclass
class Line:
    """One typeset line: its glyphs in reading order, and the baseline they share."""
    y: float
    glyphs: list[Glyph] = field(default_factory=list)
    marks: list[Glyph] = field(default_factory=list)

    @property
    def x0(self) -> float:
        return min((g.x for g in self.glyphs), default=0.0)

    @property
    def size(self) -> float:
        sizes = [g.size for g in self.glyphs]
        return max(set(sizes), key=sizes.count) if sizes else 10.0


def _baseline_groups(glyphs: list[Glyph], tolerance: float = 2.0) -> list[Line]:
    """
    Cluster glyphs onto shared baselines.

    Superscripts and subscripts sit off the baseline by design, so the tolerance is
    deliberately tight and the strays are picked up afterwards by `_attach_scripts`: a loose
    tolerance would silently fold an exponent into the body text as an ordinary digit.
    """
    lines: list[Line] = []
    for g in sorted(glyphs, key=lambda g: (-g.y, g.x)):
        for line in reversed(lines):
            if abs(line.y - g.y) <= tolerance:
                line.glyphs.append(g)
                break
        else:
            lines.append(Line(g.y, [g]))
    for line in lines:
        line.glyphs.sort(key=lambda g: g.x)
    return lines


#: Marks that are always an accent, wherever they sit: the true combining code points T1 puts
#: at 0x00-0x0C, **and the spacing modifiers** `ˇ` and `´`. The second group matters -- volume
#: 09 sets its carons with U+02C7, which sorts below U+0300 and so was being left in the text
#: as a literal character, giving `ˇze` for `že` and `súˇcet` for `súčet`.
#:
#: A comma, an apostrophe and a backtick stay out: those are punctuation far more often than
#: they are accents, and are lifted only when a whole line is made of them.
COMBINING_CHARS = ({c for c in MARKS if c >= '\u0300'} |
                   {'\u02C7', '\u00B4', '\u02D8', '\u02DA', '\u02DD'})


def _fractions(lines: list[Line], boxes: list[Box]) -> int:
    r"""
    Rebuild `\frac{}{}` from a rule and the two rows around it.

    A fraction leaves three marks in a PDF and no markup at all: a short horizontal rule, a
    row of glyphs above it and a row below, both set smaller than the text they sit in. Nothing
    says they belong together except their geometry.

    **This has to run before `_attach_scripts`**, which would otherwise take the two rows for a
    superscript and a subscript and produce `3^{}_{4}` where `\frac{3}{4}` belongs -- which is
    what `f = \frac{3}{4}\tan\alpha` was coming out as.

    Size is what separates the parts from the line they interrupt: a numerator is 9pt against
    the host's 13.5pt, and the host's own glyphs run through the same x range.
    """
    if not lines:
        return 0
    # The *modal* size, not the largest. A chapter title is the largest thing on its page, and
    # measuring against it made every line of body text count as "small" -- so on volume 09's
    # opening page the fraction pass consumed the prose itself and segmented nothing.
    weights: dict[float, int] = {}
    for ln in lines:
        if ln.glyphs:
            weights[ln.size] = weights.get(ln.size, 0) + len(ln.glyphs)
    if not weights:
        return 0
    host_size = max(weights, key=weights.get)
    small = [ln for ln in lines if ln.glyphs and ln.size < host_size * 0.9]
    built = 0

    for bar in boxes:
        if not bar.rule or bar.width > 60:
            continue
        span = (bar.x0 - 1, bar.x1 + 1)
        above, below = [], []
        for ln in small:
            reach = ln.size * 2.2
            part = [g for g in ln.glyphs if span[0] <= g.x <= span[1]]
            if not part:
                continue
            if 0 < ln.y - bar.y0 < reach:
                above.append((ln, part))
            elif 0 < bar.y0 - ln.y < reach:
                below.append((ln, part))
        if not above or not below:
            continue

        num = ''.join(g.char for _, part in above for g in part)
        den = ''.join(g.char for _, part in below for g in part)
        for ln, part in above + below:
            ln.glyphs = [g for g in ln.glyphs if g not in part]

        host = min((ln for ln in lines if ln.glyphs and ln.size >= host_size * 0.9),
                   key=lambda ln: abs(ln.y - bar.y0), default=None)
        if host is None:
            continue
        ref = host.glyphs[0]
        host.glyphs.append(Glyph(f'\\frac{{{num}}}{{{den}}}', bar.x0, host.y,
                                 bar.width, ref.size, 'math-italic', 'italic', 0, True))
        host.glyphs.sort(key=lambda g: g.x)
        built += 1
    return built


def _is_mark_row(line: Line) -> bool:
    """
    Is this whole line a raised row of accents rather than text?

    `ď ľ ť` are set with a comma-shaped mark on a baseline of its own above the line, so such a
    row is made of nothing but marks. Both `_attach_scripts` and `_lift_marks` need to know,
    and they must agree: the test lives here so it cannot be written twice and drift.
    """
    return bool(line.glyphs) and all(g.char in MARKS and not g.maths for g in line.glyphs)


def _attach_scripts(lines: list[Line]) -> None:
    r"""
    Fold exponents and indices back into the line they belong to.

    `_baseline_groups` deliberately uses a tight tolerance, so a superscript lands on a line of
    its own -- which is how `km h^{-1}` arrives as `kmh` on one line and `-1` on another, and
    how a vulgar fraction arrives as its numerator and denominator on two.

    A script line is *smaller* and *near*: a fraction of the host's size, within about
    two-thirds of it vertically. Both tests are needed. Size alone would swallow a footnote;
    proximity alone would swallow the next line of prose.

    **It goes to the nearest host, and a row of accents is not a host.** Slovak sets `ď ľ ť`
    with the mark on a raised row of its own, and such a row sits between the prose lines --
    so it is both nearer to a superscript than the line the superscript belongs to, and, being
    full size and made of ordinary comma glyphs rather than combining ones, eligible under the
    two tests above. Taking the first eligible host in document
    order put `08/p25`'s `^{-1}` on the comma row above it, which left the boat's speed
    reading `3 ms` -- three milliseconds, hoisted into `values:` and printed without complaint,
    because a millisecond is a perfectly good unit. Four of the eight booklets had one.
    """
    attached = True
    while attached:
        attached = False
        for other in [ln for ln in lines if ln.glyphs]:
            best, best_offset = None, None
            for line in lines:
                if line is other or not line.glyphs or _is_mark_row(line):
                    continue
                if other.size >= line.size * 0.85:
                    continue
                offset = other.y - line.y
                if offset == 0 or abs(offset) > line.size * 0.7:
                    continue
                if best is None or abs(offset) < abs(best_offset):
                    best, best_offset = line, offset
            if best is None:
                continue
            kind = 'sup' if best_offset > 0 else 'sub'
            best.glyphs.extend(
                Glyph(g.char, g.x, best.y, g.adv, g.size, g.role, g.style, g.code,
                      g.sure, kind)
                for g in other.glyphs)
            best.glyphs.sort(key=lambda g: g.x)
            lines.remove(other)
            attached = True
            break


def _lift_marks(lines: list[Line]) -> None:
    """
    Separate the accents from the letters. These booklets use **two** mechanisms, and missing
    either one corrupts words in a way that still reads as Slovak.

    - **Inline**: a real combining glyph (T1 0x00-0x0C) drawn on the text baseline, at the x
      of the letter it belongs to. `\v{z}` in `kužeľa` arrives as `u`, caron, `z` -- the mark
      before its base in drawing order, so sequence tells you nothing and only x does.
    - **A raised row**: a comma-shaped mark on its own baseline above the line, which is how
      `ď ľ ť` are set. `_baseline_groups` gives these a line of their own.

    A comma among words is punctuation and stays exactly where it is; lifting those moved
    every comma in the booklet to the end of its line, which reads as plausible prose and is
    not what was printed.
    """
    for line in lines:
        if _is_mark_row(line):
            line.marks, line.glyphs = line.glyphs, []          # a raised accent row
        else:
            inline = [g for g in line.glyphs if g.char in COMBINING_CHARS and not g.maths]
            if inline:
                line.glyphs = [g for g in line.glyphs if g not in inline]
                _apply(line, inline)


def _apply(target: Line, marks: list[Glyph]) -> None:
    """
    Fold marks onto the letters of one line, matching on x.

    Nearest centre, and only where the pair is a letter Slovak actually has: a mark that
    lands on something unexpected is left off rather than guessed into a wrong letter, which
    is the difference between a visible gap and a silent corruption.
    """
    for mark in marks:
        kind = MARK_KIND.get(mark.char)
        if kind is None or not target.glyphs:
            continue
        centre = mark.x + (mark.adv or target.size * 0.25) / 2
        best, best_d = None, 1e9
        for j, g in enumerate(target.glyphs):
            d = abs((g.x + g.adv / 2) - centre)
            if d < best_d:
                best, best_d = j, d
        if best is None or best_d > target.size:
            continue
        base = target.glyphs[best]
        if (composed := COMPOSE.get((base.char, kind))) is not None:
            target.glyphs[best] = Glyph(composed, base.x, base.y, base.adv,
                                        base.size, base.role, base.style, base.code)


def _compose(lines: list[Line]) -> None:
    """Fold each raised accent row into the text row beneath it."""
    for i, line in enumerate(lines):
        if not line.marks:
            continue
        if (target := next((ln for ln in lines[i + 1:] if ln.glyphs), None)) is not None:
            _apply(target, line.marks)
        line.marks = []


def _letter_shaped(box: Box) -> bool:
    """
    Is this image mask a letter, or a rule?

    Both arrive as stencil masks and there is no other way to tell them apart. A letter is
    roughly as tall as it is wide and a few points across; a rule is a hairline stretched the
    width of the text block. 10.pdf has 498 of the second kind and none of the first, so
    without this test every rule on the page splices a spurious `ý` into the prose.
    """
    if box.height <= 2 or box.width <= 1:
        return False
    return 0.25 <= box.width / box.height <= 1.2


def _splice_images(lines: list[Line], boxes: list[Box], char: str = 'ý') -> int:
    """
    Put the bitmap `ý` back into the text.

    `ý` is T1 0xFD, and 0xFD plus the encoding's shift of 3 overflows a byte -- so the single
    commonest accented letter in Slovak is the one character that could not be encoded, and
    was shipped as an image instead. It is absent from the glyph stream entirely, which is
    why a naive decode reads `rýchlosť` as `rchlos`.
    """
    spliced = 0
    for box in boxes:
        if box.kind != 'image' or not _letter_shaped(box):
            continue
        target, best_d = None, 1e9
        for line in lines:
            if not line.glyphs:
                continue
            d = abs(line.y - box.y0)
            if d < best_d:
                target, best_d = line, d
        if target is None or best_d > target.size * 1.4:
            continue
        at = len(target.glyphs)
        for j, g in enumerate(target.glyphs):
            if g.x > box.x0:
                at = j
                break
        ref = target.glyphs[min(at, len(target.glyphs) - 1)]
        # Always prose, whatever it lands next to. Inheriting the neighbour's role put the `ý`
        # of `rovný` inside the formula that followed it, which then read `rovn$ýf = …$`.
        target.glyphs.insert(at, Glyph(char, box.x0, target.y, box.width,
                                       ref.size, 't1', ref.style, 0xFD))
        spliced += 1
    return spliced


#: The fonts whose character codes are recoverable. `dcr`/`dcti` are T1 and decode exactly.
#: Everything else in these booklets -- `cmr` inside a formula, `cmmi`, `cmsy` -- is subset
#: with an index that is *not* a character code, so its glyphs cannot be read by table.
PROSE_ROLES = {'t1'}

#: What a formula is replaced by. Deliberately not LaTeX and deliberately ugly: a draft must
#: not contain something that could be mistaken for a transcribed formula.
MATH_MARK = '⟨math⟩'


def _join_maths(tokens: list[str]) -> str:
    r"""
    Join maths characters, keeping TeX macro names from running into what follows.

    `\Delta` then `t` is `\Deltat`, an undefined control sequence rather than a delta and a
    t. A control word ends at the first non-letter, so the space is not cosmetic: it is the
    only thing that terminates the name.
    """
    out: list[str] = []
    for tok in tokens:
        if (out and out[-1].startswith('\\') and out[-1][-1].isalpha()
                and tok[:1].isalnum()):
            out.append(' ')
        out.append(tok)
    return ''.join(out)


def _script_runs(run: list[Glyph]) -> list[str]:
    """Characters with `^{…}` and `_{…}` put back around the raised and lowered glyphs."""
    out: list[str] = []
    i = 0
    while i < len(run):
        kind = run[i].script
        j = i
        while j < len(run) and run[j].script == kind:
            j += 1
        body = _join_maths([g.char for g in run[i:j]])
        out.append(body if not kind else
                   ('^{%s}' if kind == 'sup' else '_{%s}') % body)
        i = j
    return out


#: A hoisted quantity, carried in the text until a problem claims it. The brackets are
#: U+27E6/U+27E7, which nothing in these booklets contains and no rule in `rules.py` touches.
HOIST = '\u27e6hoist:{key}|{symbol}|{magnitude}|{unit}\u27e7'
RE_HOIST = re.compile(r'\u27e6hoist:([^|\u27e7]*)\|([^|\u27e7]*)\|([^|\u27e7]*)\|([^\u27e7]*)\u27e7')


def _text(line: Line, values: list, missing: list[str]) -> tuple[str, list[str]]:
    """
    One line's characters, with word spaces restored -- and its formulas marked, not guessed.

    There is no space glyph in the stream: a space is a gap wider than the font would leave
    between two touching letters, measured as a fraction of the em because these booklets mix
    8pt and 12pt on the same page.

    **Formulas are replaced by a marker.** For `dcr` the glyph name carries the character code
    and the text decodes exactly; for the maths fonts it does not -- `=` is `G39`, `1` is
    `G129` and `0` is `G102` in the same font, with no constant between them, because the
    subsetter numbered glyphs by index rather than by code. Emitting a table's best guess
    there produced `s $ ccŒ1` for `s = 100 km`, which is worse than a hole: it is unreadable,
    it will not compile, and it looks enough like content to be skimmed past. So the run is
    marked and its raw glyphs are kept alongside for whoever reads the rendered page.
    """
    out: list[str] = []
    dropped: list[str] = []
    prev: Glyph | None = None
    run: list[Glyph] = []

    def flush() -> None:
        if not run:
            return
        body = ''.join(_script_runs(run))
        if all(g.sure for g in run):
            # Every glyph identified, so the formula is transcribed rather than marked.
            #
            # A run that is exactly `symbol = number unit` is a quantity the statement *gives*,
            # so it is hoisted into `values:` and printed as `(§ key.eq §)`. That is the house
            # form: the number then lives in one place, and changing it changes everywhere it
            # appears. Anything more elaborate is a formula and stays as maths.
            if (found := maths.assignment(body)) is not None:
                key, symbol, magnitude, unit = found
                values.append(found)
                # **The hoist travels inside the line, not beside it.** `values:` is a
                # per-problem mapping, and the problems are not split until much later --
                # segmentation strips furniture and reorders folios, so a line's index here
                # means nothing there. Keyed by symbol in a booklet-wide dictionary, the last
                # `v = ...` in the file silently won for every problem containing a `v`, and
                # `08/p07`'s gas vessel ended up with the volume of `08/p25`'s boat's speed.
                # So the value rides along in the placeholder and `draft.py` resolves it
                # against the problem that actually owns the line.
                out.append(HOIST.format(key=key, symbol=symbol,
                                        magnitude=magnitude, unit=unit))
            else:
                tidied, unknown = maths.tidy(body)
                missing.extend(unknown)
                out.append(f'${tidied}$')
        else:
            dropped.append(body)
            out.append(MATH_MARK)
        run.clear()

    for g in line.glyphs:
        if g.role not in PROSE_ROLES:
            if not run and prev is not None:
                gap = g.x - (prev.x + prev.adv)
                if gap > prev.size * 0.17:
                    out.append(' ')
            run.append(g)
            prev = g
            continue
        flush()
        if prev is not None:
            gap = g.x - (prev.x + prev.adv)
            if gap > prev.size * 0.17:
                out.append(' ')
        out.append(g.char)
        prev = g
    flush()
    return ''.join(out), dropped


def _dehyphenate(lines: list[str]) -> list[str]:
    """
    Rejoin a word the typesetter split across a line break.

    Only a hyphen at end of line followed by a lower-case start is joined: an em dash, a
    minus sign and a genuine compound (`fyzikálno-matematická`) all end lines too, and
    joining those would invent a word.
    """
    out: list[str] = []
    for line in lines:
        if out and out[-1].endswith('-') and line[:1].islower():
            out[-1] = out[-1][:-1] + line.lstrip()
        else:
            out.append(line)
    return out


RE_SPACES = re.compile(r'[ \t]+')


def page_text(glyphs: list[Glyph], boxes: list[Box]) -> tuple[list[str], dict]:
    """
    A page's glyphs as lines of text, plus what had to be repaired to get there.

    The report is returned rather than logged because `draft.py` puts it in `report.md`: a
    page where nothing was spliced and nothing composed is a page to look at, not a page that
    went well.
    """
    lines = _baseline_groups(glyphs)
    fractions = _fractions(lines, boxes)
    _attach_scripts(lines)
    _lift_marks(lines)
    _compose(lines)
    spliced = _splice_images(lines, boxes)

    rendered, dropped = [], []
    values: list[tuple[str, str, str, str]] = []
    missing: list[str] = []
    for ln in lines:
        if not ln.glyphs:
            continue
        text, runs = _text(ln, values, missing)
        text = RE_SPACES.sub(' ', text).strip()
        if text:
            rendered.append(text)
            dropped.extend(runs)
    report = {
        'lines': len(rendered),
        'maths-marked': len(dropped),
        'y-spliced': spliced,
        'fractions': fractions,
        'composed': sum(1 for ln in lines for g in ln.glyphs
                        if len(unicodedata.normalize('NFD', g.char)) > 1),
        'values': values,
        'unknown-units': missing,
    }
    return _dehyphenate(rendered), report
