r"""
Maths typeset at build time by MathJax, so a page needs no JavaScript and works from a directory.

pandoc leaves maths as `<span class="math inline">\(…\)</span>` for a browser to deal with. That
is fine when a page is served and useless when it is opened: Firefox gives every `file://`
document its own origin, MathJax's dynamic loads are refused, and the reader sees
`\(1.8\,\mathrm{m}\)` spelled out. Doing it here instead removes the engine, the 3.3 MB it
weighed per page directory, and the question of whether the font took.

This is the **other** engine. `texmath.py` sets the same maths with the xelatex that sets the
booklet, which is exact and makes a picture of every formula; this one makes real text that a
reader can select and a search engine can index, in Pagella, and pays for it by needing the two
things LaTeX would have done for free:

- **The expansion**, which has already happened. MathJax has no siunitx extension -- none
  exists -- and cannot express most of `math.tex`, so `Convertor.expand_for_the_web` rewrites
  both into plain maths before pandoc ever runs, through `core/filters/siunitx.py` and
  `dgsmacros.py`. A fragment reaching this point holds ordinary TeX, which is also why the
  other engine can take the same fragment: xelatex reads plain maths as happily as it reads
  `\qty`.
- **The escape hatch.** chemfig is TikZ in a lab coat, 84 times in `chem/01` alone, and no web
  implementation of it exists. Those go to LaTeX through `mathimage.py` and arrive as drawings.

One node process per page, not per formula.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import shutil
import subprocess

from core.html import mathimage, texmath

RENDERER = pathlib.Path('core/html/mathjax-render.cjs')
#: Picked by loading the font's component; naming it in `loader.font` does nothing. See the
#: comment at the top of the renderer, which was expensive to learn.
FONT = '@mathjax/mathjax-pagella-font'

#: What `npm ci` puts in `node_modules`, and what the renderer asks node for by name.
PACKAGES = ('mathjax', FONT)


def available() -> bool:
    """
    Whether this engine can run at all: node, **and the packages**.

    The two are a different question, and asking only the first is how CI came to report
    `Cannot find module '@mathjax/mathjax-pagella-font/package.json'` from inside a test that
    should have skipped -- a hosted runner has node whether or not anyone ran `npm ci`. The
    container is the other way round: it installs the packages for nobody, having no node.
    """
    return (shutil.which('node') is not None
            and all((pathlib.Path('node_modules') / name / 'package.json').is_file()
                    for name in PACKAGES))


#: What marks a fragment as beyond MathJax altogether. chemfig, and the `\schemestart`
#: environment it draws reaction arrows in; `\chemname` and `\setchemfig` only appear inside one.
BEYOND = ('chemfig', 'schemestart', 'schemestop', 'chemname', 'setchemfig')

#: What pandoc writes with `--math-method=mathjax`.
RE_MATH = re.compile(
    r'<span class="math (?P<kind>inline|display)">(?P<body>.*?)</span>', re.DOTALL)


class RenderError(RuntimeError):
    """MathJax would not typeset something. The message names the formula."""


def strip(body: str, kind: str = 'inline') -> str:
    r"""The LaTeX inside pandoc's delimiters, unescaped back from HTML."""
    text = html.unescape(body).strip()
    for opening, closing in ((r'\(', r'\)'), (r'\[', r'\]')):
        if text.startswith(opening) and text.endswith(closing):
            return text[len(opening):-len(closing)]
    return text


def beyond_mathjax(latex: str) -> bool:
    return any(f'\\{macro}' in latex for macro in BEYOND)


def shim_html(fragment: str) -> str:
    r"""
    The fragment as it stands. Kept as a seam, not as a step.

    There was a shim pass here, which ran `macros.lua` and `siunitx.lua` over every formula on
    the way to MathJax. `Convertor.expand_for_the_web` does that work now, before pandoc, so a
    fragment already holds plain maths by the time it reaches this module and a second pass
    would have nothing to rewrite.

    It stays a function because the seam is worth keeping: it is the one place a rewriting that
    belongs to *this* engine rather than to the fragment would go, and `page.py` already calls
    it on both paths.
    """
    return fragment


def typeset(fragments: list[str], lang: str = 'sk') -> list[str]:
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

    # chemfig goes to LaTeX rather than to MathJax: it is TikZ in a lab coat and no web
    # implementation of it exists.
    drawn = {i: item for i, item in enumerate(items) if beyond_mathjax(item['tex'])}
    rest = [item for i, item in enumerate(items) if i not in drawn]

    completed = subprocess.run(
        ['node', str(RENDERER)],
        input=json.dumps({'font': FONT,
                          'items': [{'tex': item['tex'], 'display': item['display']}
                                    for item in rest]}),
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise RenderError(completed.stderr.strip() or 'node would not run the renderer')
    rendered = json.loads(completed.stdout)

    failures = [(rest[i]['tex'], r['error']) for i, r in enumerate(rendered) if 'error' in r]
    if failures:
        formula, message = failures[0]
        raise RenderError(f'{len(failures)} formula(s) would not typeset; the first is '
                          f'`{formula}`: {message}')

    out_by_index, iterator = {}, iter(rendered)
    for index, item in enumerate(items):
        if index in drawn:
            out_by_index[index] = draw(item, lang)
        else:
            out_by_index[index] = next(iterator)['svg']

    # back to front, so that a replacement does not move the spans after it
    out = list(fragments)
    for index, (position, (start, stop)) in reversed(list(enumerate(places))):
        out[position] = out[position][:start] + out_by_index[index] + out[position][stop:]
    return out


def draw(item: dict, lang: str) -> str:
    """
    A fragment LaTeX has to draw, inlined the way `texmath.py` inlines its formulas.

    Inline rather than an `<img>`, because the page's pictures are collected before the maths is
    typeset: an `<img>` written here would point at the build tree and the directory would stop
    being self-contained. dvisvgm's own absolute size is kept -- a reaction scheme is a drawing,
    not a glyph, and has no business scaling with the body text.
    """
    svg = mathimage.render(item['tex'], lang).read_text()
    found = texmath.RE_SVG.search(svg)
    if not found:
        raise RenderError(f'dvisvgm produced no <svg> for `{item["tex"]}`')
    body = texmath.RE_DEFAULT_INK.sub(r"\1='currentColor'", found.group())
    body = body.replace('<svg ', '<svg class="chemistry" fill="currentColor" ', 1)
    return f'<span class="dgs-math-display">{body}</span>' if item['display'] else body
