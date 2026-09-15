r"""
Repairing the archive's SVG labels.

Every figure in the archive was drawn in Inkscape with TeX's own fonts selected by name —
`cmmi12` for maths italic, `cmr12` and `cmr7` for upright text. Those fonts are not installed
here, and **librsvg does not complain**: `fc-match cmmi12` answers *Noto Sans*, so a figure
converts with a clean exit code and the labels come out in the wrong face, upright where they
should be italic.

The repair is a style rewrite and nothing more, because the text content is already correct
Unicode — `α`, `λ`, `F`, `mg` — not cm glyph slots. `cmmi` is maths italic and every label in it
is a variable, so it takes `font-style:italic`; `cmr` is upright. Both become `'Minion Pro'`,
which is what the 145 modern figures in this repository already use.

Two things to know. A `<tspan>` can override its parent `<text>` — `KIN/zavodny_zad.svg` has a
cmmi span inside a cmr text — so every style declaration is treated on its own rather than only
the `<text>` elements. And metrics are the residual risk: Minion is narrower than cmmi and these
labels are absolutely positioned, so a label centred on an arrowhead can drift. Look at the
result; a clean exit proves nothing.
"""
import re

HOUSE = "'Minion Pro'"

#: family -> is it maths italic? `cmmi` and `cmsy` are; `cmr` and `cmex` are not.
CM_FAMILIES = {
    'cmmi5': True, 'cmmi7': True, 'cmmi8': True, 'cmmi9': True, 'cmmi10': True, 'cmmi12': True,
    'cmsy7': True, 'cmsy10': True,
    'cmr5': False, 'cmr7': False, 'cmr8': False, 'cmr9': False, 'cmr10': False, 'cmr12': False,
    'cmex10': False, 'cmbx12': False, 'cmti12': True,
}

#: Families that are already fine, so neither rewritten nor reported.
ACCEPTED = {'minion pro', 'sans-serif', 'serif', 'sans', 'monospace'}

#: One `style="…"` attribute, or one `font-family="…"` XML attribute.
RE_STYLE = re.compile(r'style="([^"]*)"')
RE_ATTR_FAMILY = re.compile(r'font-family="([^"]*)"')
RE_FAMILY = re.compile(r"font-family:\s*'?([^;'\"]+?)'?\s*(?=;|$)")


def _rewrite_style(block: str, others: list[str]) -> tuple[str, int]:
    """One CSS declaration list. Returns the new text and how many families were replaced."""
    m = RE_FAMILY.search(block)
    if not m:
        return block, 0
    family = m.group(1).strip()
    if family not in CM_FAMILIES:
        if family.lower() not in ACCEPTED:
            others.append(family)
        return block, 0

    italic = CM_FAMILIES[family]
    block = RE_FAMILY.sub(lambda _: f'font-family:{HOUSE}', block, count=1)
    spec = f"'Minion Pro, {'Italic' if italic else 'Normal'}'"
    if '-inkscape-font-specification:' in block:
        block = re.sub(r"-inkscape-font-specification:\s*'?[^;']*'?",
                       lambda _: f'-inkscape-font-specification:{spec}', block)
    else:
        block += f';-inkscape-font-specification:{spec}'
    want = 'italic' if italic else 'normal'
    if re.search(r'font-style:\s*[a-zA-Z]+', block):
        block = re.sub(r'font-style:\s*[a-zA-Z]+', lambda _: f'font-style:{want}', block)
    else:
        block = f'font-style:{want};' + block
    return block, 1


def repair(svg: str) -> tuple[str, list[str], int]:
    """
    Rewrite every CM font family in an SVG to Minion Pro.

    Returns the new SVG, any other non-house families found (reported, never touched — a
    `Comic Sans MS` in a figure may well be the joke), and the number of replacements.
    """
    others: list[str] = []
    count = 0

    def style(m: re.Match) -> str:
        nonlocal count
        new, n = _rewrite_style(m.group(1), others)
        count += n
        return f'style="{new}"'

    out = RE_STYLE.sub(style, svg)

    def attr(m: re.Match) -> str:
        nonlocal count
        family = m.group(1).strip().strip("'")
        if family not in CM_FAMILIES:
            if family.lower() not in ACCEPTED:
                others.append(family)
            return m.group(0)
        count += 1
        return 'font-family="Minion Pro"'

    out = RE_ATTR_FAMILY.sub(attr, out)
    return out, sorted(set(others)), count
