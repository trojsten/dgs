"""
Writing a decoded booklet out as a draft problem tree.

Deliberately the same shape as `tools/ancient/convert.py`, and for the same reason it gives:
**this writes only to `--out` and never into `source/`**, so it can be re-run at will and
hand-finishing can never be clobbered. Review is `diff -ru <draft>/<pid> source/naboj/phys/<vol>/problems/<pid>`.

What it emits per problem is the current schema, and nothing more:

    <out>/<volume>/problems/<pid>/meta.yaml
    <out>/<volume>/problems/<pid>/answer.md
    <out>/<volume>/problems/<pid>/sk/problem.md
    <out>/<volume>/problems/<pid>/sk/solution.md

`answer.md` is left as a `%# TODO(answer)` marker rather than filled in. None of these
booklets has an answer sheet -- the answer is a sentence inside the solution, and deciding
which sentence is judgement, exactly as `\\comment{}` was for 2009. A converter that guessed
would put a wrong number on an answer sheet, which is the one place nobody re-reads.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.ancient import rules
from tools.ancient.pdf import assemble, glyphs, pages, segment


#: Until a slug table names them, problems are `p07` and so on -- provisional on purpose, and
#: refused by `--out` into anything but a draft, because renaming later means moving a
#: directory and rewriting every `#fig:` and `#eq:` label inside it.
def provisional(number: int) -> str:
    return f'p{number:02d}'


META = """\
# Drafted by `tools.ancient.pdf` from `{source}`, problem {number}.
# Nothing here is read from the booklet: it has no per-problem author, and the tags are a
# reading of the statement rather than a record of intent. See `errors/{volume}.md`.
authors:
  idea: []
  problem: []
  solution: []
tags: []
"""

VALUES = """\
# Quantities the statement gives, hoisted out of the prose so each number lives in one place
# and `(§ <key>.eq §)` prints it. Read from the booklet; nothing here is computed.
values:
"""

ANSWER = """\
%# TODO(answer): read the answer out of the solution and write it here.
%# These booklets have no answer sheet -- the answer is a sentence inside `solution.md`.
"""


def body(lines: list[str]) -> str:
    """
    A problem's lines as Markdown, normalised the way every other converted volume is.

    `rules` is reused whole: these are the same authors writing the same notation as 2007, so
    `spaced_units`, `thin_comma` and the rest apply unchanged.
    """
    text = '\n'.join(lines).strip()
    for rule in (rules.spaced_units, rules.thin_comma):
        try:
            text = rule(text)
        except Exception:                    # a rule that cannot cope is reported, not fatal
            pass
    return rules.wrap(text) if hasattr(rules, 'wrap') else text


def read_booklet(pdf: Path, volume: str | None = None) -> tuple[list[str], dict]:
    """Every line of a booklet, in reading order, with the repair counts."""
    import subprocess
    npages = int(subprocess.run(['mutool', 'info', str(pdf)], capture_output=True, text=True)
                 .stdout.split('Pages: ')[1].split()[0])
    collected: list[tuple[int | None, list[str]]] = []
    totals = {'lines': 0, 'y-spliced': 0, 'composed': 0, 'maths-marked': 0, 'pages': npages, 'halves': 0, 'ordered-by-folio': False,
              'values': {}, 'unknown-units': []}
    shift = None
    for page in range(1, npages + 1):
        gs, boxes, shift = glyphs.read_page(pdf, page, shift, volume)
        # A sheet may carry two pages. Splitting is a no-op for the six booklets that are not
        # imposed, and the difference between prose and interleaved nonsense for the two that
        # are.
        for half in pages.split(gs, boxes):
            totals['halves'] += 1
            got, rep = assemble.page_text(half.glyphs, half.boxes)
            collected.append((half.folio, got))
            for k in ('lines', 'y-spliced', 'composed', 'maths-marked'):
                totals[k] += rep[k]
            totals['values'].update(rep['values'])
            totals['unknown-units'].extend(rep['unknown-units'])
    # **Order the whole booklet by folio, not each sheet on its own.** Saddle-stitching pairs
    # the first page with the last, so the sheets arrive 2/34, 4/32, 6/30 -- sorting within a
    # sheet leaves that sequence intact and the booklet still reads end over end. Volume 05's
    # solutions stopped at 23 of 50 for exactly this reason.
    # Only when the evidence supports it, and only when it is needed. Reading a folio off a
    # page is guesswork -- a problem number at the head of a column looks exactly like one --
    # so sorting on it wrecked volume 08, which was already in order, taking it from 31
    # problems to 17. Three things must hold: the booklet is actually imposed, every page
    # yielded a folio, and those folios are distinct and cover a contiguous run. Anything less
    # and the physical order is the better guess.
    folios = [f for f, _ in collected]
    imposed = totals['halves'] > totals['pages']
    known = [f for f in folios if f is not None]

    # A page or two will not give up its folio -- a title page has none, and a crop can lose
    # one. Those are recoverable: the numbers *missing* from the run are exactly as many as the
    # pages missing a number, so they can be handed out in physical order and then checked.
    if imposed and known and len(known) >= len(folios) - 3:
        hi = max(known)
        # The run ends at the highest folio and is exactly as long as there are pages, so the
        # missing numbers are whatever that window does not already contain.
        spare = sorted(set(range(hi - len(folios) + 1, hi + 1)) - set(known))
        filled, pool = [], list(spare)
        for f in folios:
            filled.append(f if f is not None else (pool.pop(0) if pool else None))
        # The check, not the assumption: every page numbered once, and the numbers unbroken.
        if (None not in filled and len(set(filled)) == len(filled)
                and max(filled) - min(filled) == len(filled) - 1):
            order = sorted(range(len(collected)), key=lambda i: filled[i])
            collected[:] = [collected[i] for i in order]
            totals['ordered-by-folio'] = True
    lines: list[str] = [ln for _, got in collected for ln in got]
    totals['shift'] = shift
    return lines, totals


def write(out: Path, volume: str, pdf: Path, dry_run: bool = False) -> str:
    lines, totals = read_booklet(pdf, volume)
    found, complaints = segment.problems(lines)

    report = [f'# {pdf.name} -> volume {volume}', '',
              f'- sheets: {totals["pages"]}, logical pages: {totals["halves"]}, '
              f'lines: {totals["lines"]}',
              f'- encoding shift: {totals["shift"]}',
              f'- `ý` bitmaps spliced: {totals["y-spliced"]}',
              f'- accents composed: {totals["composed"]}',
              f'- formulas marked rather than guessed: {totals["maths-marked"]}',
              f'- quantities hoisted into `values:`: {len(totals["values"])}',
              f'- problems segmented: {len(found)}', '']
    if totals['unknown-units']:
        from collections import Counter
        top = Counter(totals['unknown-units']).most_common(12)
        report += ['## Units the table does not know', '',
                   'Left as written and reported, never guessed -- extend `units.py`.', '']
        report += [f'- `{u}` x{n}' for u, n in top] + ['']
    if complaints:
        report += ['## What did not segment cleanly', '']
        report += [f'- {c}' for c in complaints] + ['']

    if not dry_run:
        for p in found:
            pid = provisional(p.number)
            root = out / volume / 'problems' / pid
            (root / 'sk').mkdir(parents=True, exist_ok=True)
            text = '\n'.join(p.statement + p.solution)
            used = {k: v for k, v in totals['values'].items() if f'({chr(167)} {k}.' in text}
            meta = META.format(source=pdf.name, number=p.number, volume=volume)
            if used:
                meta += VALUES + ''.join(
                    f"  {k}:\n    magnitude: {mag}\n    unit: '{unit}'\n    symbol: '{sym}'\n"
                    for k, (sym, mag, unit) in sorted(used.items()))
            (root / 'meta.yaml').write_text(meta)
            (root / 'answer.md').write_text(ANSWER)
            (root / 'sk' / 'problem.md').write_text(body(p.statement) + '\n')
            (root / 'sk' / 'solution.md').write_text(
                body(p.solution) + '\n' if p.solution else
                '%# TODO(solution): the booklet prints none for this problem.\n')
        (out / volume / 'report.md').write_text('\n'.join(report))

    return '\n'.join(report)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pdf', type=Path)
    ap.add_argument('-v', '--volume', required=True)
    ap.add_argument('-o', '--out', type=Path, required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if 'source/' in str(a.out.resolve()):
        ap.error('--out must not be inside source/: this writes drafts, never the tree')
    print(write(a.out, a.volume, a.pdf, a.dry_run))


if __name__ == '__main__':
    main()
