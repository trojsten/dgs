"""
A booklet's lines into numbered problems.

Every one of these booklets has the same two-chapter shape -- `Zadania` then `Riešenia` --
and numbers its problems from 1 in each. So a problem is a run of lines between one number
and the next, and the two chapters are joined on that number.

The numbering is the check as well as the key: a booklet that does not yield an unbroken
1..N in both chapters has been segmented wrongly, and saying so is more use than emitting
39 problems and one silent mess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: A running header, which repeats on every page and is never content.
RE_HEADER = re.compile(r'^\s*\d?\.?\s*(Zadania|Rie[sš]enia)\s*\d*\s*$')
#: The chapter openings themselves.
RE_CHAPTER = re.compile(r'(Zadania|Rie[sš]enia)')
#: `12.` or `12 .` at the head of a line, which is how every problem starts.
RE_ITEM = re.compile(r'^\s*(\d{1,2})\s*\.\s+(\S.*)$')

#: The same thing *inside* a line, after a sentence has ended. Volume 02 sets its solutions as
#: running prose rather than one paragraph each, so the fourteenth begins halfway along the
#: line that finishes the thirteenth -- `… teda $a_1 = a_2$. 14. Nech vzdialenosť …`. Anchoring
#: on the line start alone found eleven solutions of thirty-six.
RE_INLINE_ITEM = re.compile(r'(?<=[.?!])\s+(\d{1,2})\s*\.\s+(?=\S)')
#: The chapter's own title, which is what opens the solutions. **This has to be looked for
#: before the running header**, because the opening page of a chapter carries no running head
#: -- so splitting on the header lands on the *second* page of solutions and silently drops
#: however many were printed on the first. In 07 that was five of forty-five.
RE_TITLE = re.compile(r'(?:Kapitola\s*\d+\s*)?Rie[sš]enia')

#: A bare page number on its own line.
RE_FOLIO = re.compile(r'^\s*\d{1,3}\s*$')


@dataclass
class Problem:
    """One problem, as the booklet printed it."""
    number: int
    statement: list[str] = field(default_factory=list)
    solution: list[str] = field(default_factory=list)


def _strip_furniture(lines: list[str]) -> list[str]:
    """Drop running headers and folios, which otherwise land inside a problem's text."""
    return [ln for ln in lines if not RE_HEADER.match(ln) and not RE_FOLIO.match(ln)]


def _split_chapters(lines: list[str]) -> tuple[list[str], list[str]]:
    """
    (statements, solutions), split where **the numbering restarts**.

    Neither landmark in the document is reliable. The chapter title is set in a display font
    that does not always decode, and the running header is absent from the chapter's opening
    page -- so splitting on the header lands on the *second* page of solutions and silently
    drops whatever was printed on the first. In 07 that was five of forty-five.

    What is reliable is the numbering itself: both chapters count from 1, so the boundary is
    where a `1.` appears after the count has climbed. That needs no furniture at all, which is
    why it survives a booklet whose typography differs from its neighbours'.
    """
    candidates = [i for i, ln in enumerate(lines)
                  if (m := RE_ITEM.match(ln)) and int(m.group(1)) == 1]
    if len(candidates) < 2:
        return lines, []

    # A statement may itself contain an enumerated list, so a `1.` is not on its own evidence
    # of the chapter boundary -- taking the first one found eight problems where there are
    # forty-five. The boundary is the split that leaves *both* halves with a long unbroken
    # run, which only the real one does: a list inside a statement gives a short run on one
    # side and a truncated chapter on the other.
    best, best_score = None, 0
    for i in candidates:
        score = min(len(_items(lines[:i])), len(_items(lines[i:])))
        if score > best_score:
            best, best_score = i, score
    return (lines[:best], lines[best:]) if best else (lines, [])


def _items(lines: list[str]) -> list[tuple[int, list[str]]]:
    """
    Runs of lines keyed by the number that opens them.

    A number only opens an item if it is roughly the one expected next. That single rule keeps
    a date, a figure caption or a `2.` inside a sentence from starting a spurious problem, and
    it is why the result can be trusted as a running order rather than a guess. A small forward
    jump is allowed, because an item can be missing from the glyph stream: volume 04's solution
    8 is, and a strict rule stopped there and lost the remaining thirty-nine.

    An item may also begin *partway along a line*. Volume 02 sets its solutions as running
    prose rather than one paragraph each, so the fourteenth starts on the line that finishes
    the thirteenth. Only the expected number splits a line -- any other digit before a stop is
    a date or the end of a sentence, and splitting on those would shred the prose.
    """
    out: list[tuple[int, list[str]]] = []
    want = 1

    def take(line: str) -> None:
        nonlocal want
        if (m := RE_ITEM.match(line)) and want <= (n := int(m.group(1))) <= want + 3:
            out.append((n, [m.group(2)]))
            want = n + 1
        elif out:
            out[-1][1].append(line)

    for raw in lines:
        rest = raw
        while (m := RE_INLINE_ITEM.search(rest)):
            n = int(m.group(1))
            head = rest[:m.start()]
            if not (want <= n <= want + 3 and head.strip()):
                break
            take(head)
            rest = rest[m.start():].lstrip()
        take(rest)
    return out


def problems(lines: list[str]) -> tuple[list[Problem], list[str]]:
    """
    Every problem in a booklet, and what went wrong.

    Complaints are returned rather than raised: a booklet whose solutions stop at 28 is still
    worth converting, and `draft.py` puts the complaint in `report.md` where it can be acted
    on per problem instead of stopping the whole year.
    """
    # Strip the furniture *first*. A running header reads `1. Zadania 3`, which matches the
    # shape of an item exactly -- so with the headers left in, every page of statements looked
    # like a chapter boundary and the real one was indistinguishable from them. This is safe
    # now only because the split is on the numbering rather than on the header itself.
    lines = _strip_furniture(lines)
    zad, rie = _split_chapters(lines)
    statements, solutions = _items(zad), dict(_items(rie))

    complaints: list[str] = []
    if not statements:
        complaints.append('no statements found: the `Zadania` chapter did not segment')
    if not solutions:
        complaints.append('no solutions found: the `Riešenia` chapter did not segment')

    found = [Problem(n, body, solutions.get(n, [])) for n, body in statements]
    for p in found:
        if not p.solution:
            complaints.append(f'problem {p.number} has no solution in the booklet')
    extra = set(solutions) - {p.number for p in found}
    for n in sorted(extra):
        complaints.append(f'solution {n} has no statement')
    return found, complaints
