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

- **The shims.** MathJax has no siunitx extension -- none exists -- and cannot express most of
  `math.tex`. `core/filters/macros.lua` and `siunitx.lua` rewrite both into plain maths, and
  they run here rather than in the convertor so that `build/**.html` stays engine-neutral: the
  same fragments serve either engine, and switching costs a page rebuild, not a pandoc rebuild.
- **The escape hatch.** chemfig is TikZ in a lab coat, 84 times in `chem/01` alone, and no web
  implementation of it exists. Those go to LaTeX through `mathimage.py` and arrive as drawings.

One node process per page, not per formula.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import subprocess

from core.html import mathimage, texmath

RENDERER = pathlib.Path('core/html/mathjax-render.cjs')
#: Picked by loading the font's component; naming it in `loader.font` does nothing. See the
#: comment at the top of the renderer, which was expensive to learn.
FONT = '@mathjax/mathjax-pagella-font'

#: The shims, in order: `macros.lua` expands `math.tex`, `siunitx.lua` the units it leaves.
SHIMS = ('core/filters/macros.lua', 'core/filters/siunitx.lua')

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


def api_version() -> list[int]:
    """
    Pandoc's AST version, asked of pandoc rather than written down.

    The JSON reader refuses a document whose version it does not recognise, and the number moves
    with pandoc -- hard-coding it would make an upgrade fail here, a long way from the cause.
    """
    out = subprocess.run(['pandoc', '-f', 'markdown', '-t', 'json'],
                         input='', capture_output=True, text=True, check=True)
    return json.loads(out.stdout)['pandoc-api-version']


def shim(items: list[dict]) -> list[str]:
    r"""
    Every formula through `macros.lua` and `siunitx.lua`, which is where `\Diff` and `\qty` go.

    Over the AST rather than over Markdown: the fragments came *out* of pandoc's own maths
    parser, and feeding them back in as `$…$` would ask it to parse them a second time, with a
    second set of chances to read one differently. A `Math` node built here cannot be misread.
    """
    if not items:
        return []
    blocks = [{'t': 'Para', 'c': [{'t': 'Math', 'c': [
        {'t': 'DisplayMath' if item['display'] else 'InlineMath'}, item['tex']]}]}
        for item in items]
    document = {'pandoc-api-version': api_version(), 'meta': {}, 'blocks': blocks}

    args = ['pandoc', '-f', 'json', '-t', 'json']
    for filter_ in SHIMS:
        args += ['--lua-filter', f'./{filter_}']
    completed = subprocess.run(args, input=json.dumps(document),
                               capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        # a filter that stopped on purpose -- `siunitx.lua` naming a unit it has no symbol for
        raise RenderError(completed.stderr.strip() or 'a shim filter would not run')

    out = [block['c'][0]['c'][1] for block in json.loads(completed.stdout)['blocks']]
    if len(out) != len(items):
        raise RenderError(f'the shims returned {len(out)} formulas of {len(items)}')
    return out


def shim_html(fragment: str) -> str:
    r"""
    One fragment with every formula rewritten in place, and nothing else done to it.

    The shims are the half of this engine that can be read: `\qty{3}{\metre\per\second}`
    becomes `3\,\mathrm{m}/\mathrm{s}` and stays a `<span class="math">`, so a test can say
    what siunitx prints without starting node. `typeset` does this and then hands the result to
    MathJax.
    """
    items = [{'tex': strip(m['body'], m['kind']), 'display': m['kind'] == 'display'}
             for m in RE_MATH.finditer(fragment)]
    if not items:
        return fragment
    rewritten = iter(shim(items))

    def put(match):
        opening, closing = (r'\[', r'\]') if match['kind'] == 'display' else (r'\(', r'\)')
        return (f'<span class="math {match["kind"]}">'
                f'{opening}{next(rewritten)}{closing}</span>')

    return RE_MATH.sub(put, fragment)


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

    # chemfig first, and before the shims see it: those would rewrite a `\qty` inside a scheme
    # that LaTeX is about to set perfectly well itself
    drawn = {i: item for i, item in enumerate(items) if beyond_mathjax(item['tex'])}
    rest = [item for i, item in enumerate(items) if i not in drawn]

    shimmed = shim(rest)
    completed = subprocess.run(
        ['node', str(RENDERER)],
        input=json.dumps({'font': FONT,
                          'items': [{'tex': tex, 'display': item['display']}
                                    for tex, item in zip(shimmed, rest, strict=True)]}),
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
