r"""
Checking a converted volume against the booklet it came from.

The comparison a person would make is to hold the rendered page beside the scan and read both,
which is tedious and, for three hundred and fifty problems, not going to happen evenly. Most of
it is mechanical, though, and the mechanical part is the part that matters: **a number that
changed between the two is the failure nobody catches by eye.**

Two checks, and they answer different questions.

`digits` compares every run of digits in the decoded booklet against the rendered output, in
order, per problem. It is deliberately blind to units, markup, spacing and wording -- a
statement may be rewritten and an equation hoisted without moving a digit. What it catches is
`400/27` printing as `400/2`, which is what a dropped glyph looks like, and `\qty{5}{\percent}`
where the page says 75, which is what a lost digit looks like after the fact.

`units` finds a magnitude the source leaves as prose: `15ms^{-1}` where the house form is
`\qty{15}{\metre\per\second}`. That is a style gap rather than an error -- the page shows the
same thing either way -- but it is the gap that hides the errors, because a quantity outside
`\qty{}` is a quantity `siunitx` never checked and the audit never saw.
"""

from __future__ import annotations

import re

#: A run of digits, with a decimal separator kept inside it: `88,10` is one number and not two.
RE_DIGITS = re.compile(r'\d+(?:[.,]\d+)*')

#: A magnitude immediately followed by letters, which is a quantity written out as prose. The
#: exponent form is included -- `ms^{-1}` is how these booklets write a speed.
RE_BARE_UNIT = re.compile(r'(?<![\w\\{])(\d+(?:[.,]\d+)?)\s*'
                          r'([A-Za-z]{1,4}(?:\s*/\s*[A-Za-z]{1,3})?(?:\^\{?-?\d\}?)?)(?![\w}])')

#: Words that follow a number without being a unit. Slovak counts things in the middle of a
#: sentence -- `2 body`, `3 dosky` -- and a bare `\qty` rule would make a unit of every one.
NOT_UNITS = {
    'a', 'aj', 'ak', 'ako', 'alebo', 'az', 'až', 'bod', 'bodu', 'body', 'bodov', 'cm3',
    'da', 'do', 'dosky', 'dva', 'guli', 'hran', 'i', 'je', 'ked', 'keď', 'krat', 'krát',
    'kusov', 'na', 'nad', 'no', 'o', 'od', 'plat', 'po', 'pod', 'pre', 'prve', 'pri', 's',
    'sa', 'stran', 'sú', 'su', 'ta', 'tak', 'te', 'to', 'tri', 'tyc', 'v', 'vo', 'z', 'za',
    'ze', 'že',
}


#: Anything whose digits are not the booklet's. An image path is the converter's own invention
#: -- `figure-1.svg` against an empty one -- and a `%#` note is a message to whoever reads the
#: source, neither of which the printed page ever had.
RE_NOT_THE_BOOKLETS = re.compile(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?|^%#.*$', re.MULTILINE)

#: A superscript exponent, dropped from both sides. `ms^{-1}` and `\metre\per\second` are the
#: same unit and only one of them spells the 1, so a reciprocal unit converted correctly would
#: otherwise read as a lost digit. A real exponent -- `v^{2}` -- stands on both sides and loses
#: nothing by going.
RE_EXPONENT = re.compile(r'\^\{?-?\d+\}?')


def _comparable(text: str) -> str:
    """The text with the converter's own furniture taken out."""
    return RE_EXPONENT.sub(' ', RE_NOT_THE_BOOKLETS.sub(' ', text))


def digits(original: str, rendered: str) -> tuple[list[str], list[str]]:
    """
    (digits the booklet has and the page does not, digits the page has and the booklet does
    not), counted as characters rather than as numbers.

    **Characters, because a repaired fraction regroups them.** A fraction arrives from the
    decode as three rows of text, so `\frac{1}{2}` reads as the run `22222` in one place and as
    five separate `2`s once it is rebuilt; comparing runs calls that five losses and five gains
    and buries the one real change underneath. The digits themselves do not move, and a digit
    that appears or vanishes is the thing worth stopping for.

    The decimal separator is normalised away: the source writes `88.10` because siunitx refuses
    a comma, and the page prints `88,10` from the Slovak locale. That is one number twice.
    """
    from collections import Counter
    def characters(text: str) -> Counter:
        return Counter(c for c in _comparable(text) if c.isdigit())
    was, now = characters(original), characters(rendered)
    return sorted((was - now).elements()), sorted((now - was).elements())


def runs(original: str, rendered: str) -> tuple[list[str], list[str]]:
    """The same comparison on whole numbers, which is noisier but names what moved."""
    from collections import Counter
    norm = lambda s: [n.replace(',', '.') for n in RE_DIGITS.findall(_comparable(s))]
    was, now = Counter(norm(original)), Counter(norm(rendered))
    return sorted((was - now).elements()), sorted((now - was).elements())


def bare_units(rendered: str) -> list[str]:
    """Every magnitude the source writes as prose rather than through `\\qty`."""
    stripped = re.sub(r'\\qty\{[^}]*\}\{[^}]*\}|\\num\{[^}]*\}|\\ang\{[^}]*\}', ' ', rendered)
    out = []
    for m in RE_BARE_UNIT.finditer(stripped):
        tail = m.group(2).strip()
        if tail.lower() in NOT_UNITS or tail.isdigit():
            continue
        out.append(m.group(0).strip())
    return out
