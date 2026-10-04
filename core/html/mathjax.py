r"""
Maths typeset at build time, so a page needs no JavaScript and works from a directory.

pandoc leaves maths as `<span class="math inline">\(…\)</span>` for a browser to deal with. That
is fine when a page is served and useless when it is opened: Firefox gives every `file://`
document its own origin, MathJax's dynamic loads are refused, and the reader sees
`\(1.8\,\mathrm{m}\)` spelled out. Doing it here instead removes the engine, the 3.3 MB it
weighed per page directory, and the question of whether the font took.

One node process per page, not per formula.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import subprocess

RENDERER = pathlib.Path('core/html/mathjax-render.cjs')
#: Picked by loading the font's component; naming it in `loader.font` does nothing. See the
#: comment at the top of the renderer, which was expensive to learn.
FONT = '@mathjax/mathjax-pagella-font'

#: What pandoc writes with `--math-method=mathjax`.
RE_MATH = re.compile(
    r'<span class="math (?P<kind>inline|display)">(?P<body>.*?)</span>', re.DOTALL)


class RenderError(RuntimeError):
    """MathJax would not typeset something. The message names the formula."""


def strip(body: str, kind: str) -> str:
    r"""The LaTeX inside pandoc's delimiters, unescaped back from HTML."""
    text = html.unescape(body).strip()
    for opening, closing in ((r'\(', r'\)'), (r'\[', r'\]')):
        if text.startswith(opening) and text.endswith(closing):
            return text[len(opening):-len(closing)]
    return text


def typeset(fragments: list[str]) -> list[str]:
    """
    Every formula in every fragment, replaced by its SVG.

    Batched across the whole page: node takes about a second to start and a millisecond a
    formula, so one process for two hundred of them is the difference between a build and a
    coffee break.
    """
    items, places = [], []
    for index, text in enumerate(fragments):
        for match in RE_MATH.finditer(text):
            items.append({'tex': strip(match['body'], match['kind']),
                          'display': match['kind'] == 'display'})
            places.append((index, match.span()))
    if not items:
        return list(fragments)

    completed = subprocess.run(
        ['node', str(RENDERER)],
        input=json.dumps({'font': FONT, 'items': items}),
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise RenderError(completed.stderr.strip() or 'node would not run the renderer')
    rendered = json.loads(completed.stdout)

    failures = [(items[i]['tex'], r['error']) for i, r in enumerate(rendered) if 'error' in r]
    if failures:
        formula, message = failures[0]
        raise RenderError(f'{len(failures)} formula(s) would not typeset; the first is '
                          f'`{formula}`: {message}')

    # back to front, so that a replacement does not move the spans after it
    out = list(fragments)
    for (index, (start, stop)), result in reversed(list(zip(places, rendered, strict=True))):
        out[index] = out[index][:start] + result['svg'] + out[index][stop:]
    return out
