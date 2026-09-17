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
    (statements, solutions), split on the **running header**.

    Not on the chapter title. The title is a single line reading `Riešenia`, which is also
    exactly what the running header reduces to once its folio is stripped -- so stripping the
    furniture first deletes the title, and looking for the title first means finding whichever
    the stripper left behind. The header is the reliable landmark because it repeats: the
    first page carrying `2. Riešenia` at the top is the first page of solutions, whatever the
    title page looks like.
    """
    for i, ln in enumerate(lines):
        if (m := RE_HEADER.match(ln)) and 'Rie' in m.group(1):
            return lines[:i], lines[i:]
    return lines, []


def _items(lines: list[str]) -> list[tuple[int, list[str]]]:
    """
    Runs of lines keyed by the number that opens them.

    A number only opens a problem if it is the one expected next. That single rule keeps a
    date, a figure caption or `2.` inside a sentence from starting a spurious problem, and it
    is why the result can be trusted as a running order rather than a guess.
    """
    out: list[tuple[int, list[str]]] = []
    want = 1
    for ln in lines:
        m = RE_ITEM.match(ln)
        if m and int(m.group(1)) == want:
            out.append((want, [m.group(2)]))
            want += 1
        elif out:
            out[-1][1].append(ln)
    return out


def problems(lines: list[str]) -> tuple[list[Problem], list[str]]:
    """
    Every problem in a booklet, and what went wrong.

    Complaints are returned rather than raised: a booklet whose solutions stop at 28 is still
    worth converting, and `draft.py` puts the complaint in `report.md` where it can be acted
    on per problem instead of stopping the whole year.
    """
    # Split first, strip second: the furniture and the chapter title are the same string.
    zad, rie = _split_chapters(lines)
    statements = _items(_strip_furniture(zad))
    solutions = dict(_items(_strip_furniture(rie)))

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
