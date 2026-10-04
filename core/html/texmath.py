r"""
Maths on the web, set by the LaTeX that sets the booklet.

MathJax under node gets a page typeset without a browser, and it gets it in Pagella, because no
MathJax font for MinionPro exists or can be made from an OTF. This takes the other road: hand
every formula to xelatex with `core/latex/math.tex`, `siunitx.tex` and MinionPro loaded, and put
the SVG it gives back into the page. The maths then *is* the booklet's maths rather than
something close to it, down to the `\DeclarePairedDelimiter`s and MnSymbol's operators.

Two things make it practical rather than merely faithful.

**One xelatex run per page, not per formula.** `standalone`'s `multi=` option puts each
environment on its own page, so a hundred formulas cost one compile and one `dvisvgm`.

**The baseline is measured, not guessed.** An image does not know where its baseline sits, which
is what dropped every inline formula onto a line of its own the first time this was tried. The
template reports each box's height, depth and the font's x-height; `height` and `vertical-align`
in `ex` follow from those three, and the formula sits on the text's baseline and scales with it.
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import subprocess

from core.builder.context import Context
from core.builder.jinja import StaticRenderer

TEMPLATE_ROOT = pathlib.Path('core/templates')
TEMPLATE = 'mathpage.jtex'
CACHE = pathlib.Path('build/.html-math')

#: In the hash, so that changing the wrapper or the conversion invalidates what it produced.
VERSION = '3'

#: What pandoc writes with `--math-method=mathjax`.
RE_MATH = re.compile(r'<span class="math (?P<kind>inline|display)">(?P<body>.*?)</span>',
                     re.DOTALL)
RE_METRIC = re.compile(r'^DGSMETRIC ([\d.]+)pt ([\d.]+)pt ([\d.]+)pt$', re.MULTILINE)
#: dvisvgm writes a whole document; only the `<svg>` goes into the page.
RE_SVG = re.compile(r'<svg\b.*?</svg>', re.DOTALL)
#: `stroke='#000'` on a rule, as against a colour the drawing asked for. See `inline_svg`.
RE_DEFAULT_INK = re.compile(r"\b(stroke|fill)='#000(?:000)?'")


class RenderError(RuntimeError):
    """LaTeX would not set the page's maths. The message carries its complaint."""


def digest(latex: str, lang: str, display: bool) -> str:
    return hashlib.sha1(
        f'{VERSION}\0{lang}\0{int(display)}\0{latex}'.encode()).hexdigest()[:32]


def strip(body: str) -> str:
    r"""The LaTeX inside pandoc's `\(…\)` or `\[…\]`."""
    text = html.unescape(body).strip()
    for opening, closing in ((r'\(', r'\)'), (r'\[', r'\]')):
        if text.startswith(opening) and text.endswith(closing):
            return text[len(opening):-len(closing)].strip()
    return text


def inline_svg(svg: str, height: float, depth: float, exheight: float, display: bool) -> str:
    """
    The SVG, sized in `ex` and sitting on the baseline.

    Inlined into the page rather than linked, so that one file is the whole document and so that
    `fill="currentColor"` can take the page's text colour -- which is what makes dark mode work
    without a second rendering.

    The size is in `ex` and the width is left off entirely: the `viewBox` gives the aspect ratio,
    so the browser derives the width, and the formula grows and shrinks with the type around it.
    """
    # A glyph is a filled path with no `fill` of its own, so the root's `currentColor` reaches
    # it. A *rule* is not a glyph: a fraction bar, a `\sqrt` overbar, a `\hline` are stroked
    # paths dvisvgm gives an explicit `stroke='#000'`, which overrides anything inherited --
    # so in dark mode every fraction kept a black bar under white digits. Only the default ink
    # is rewritten; a colour the drawing actually chose is left alone.
    svg = RE_DEFAULT_INK.sub(r"\1='currentColor'", svg)
    opening = svg[:svg.index('>') + 1]
    total, drop = (height + depth) / exheight, depth / exheight
    style = f'height: {total:.3f}ex'
    if not display:
        style += f'; vertical-align: {-drop:.3f}ex'
    replaced = re.sub(r" (?:width|height)='[^']*'", '', opening)
    replaced = replaced.replace(
        '<svg ', f'<svg class="dgs-math" fill="currentColor" style="{style}" ', 1)
    svg = replaced + svg[len(opening):]
    return f'<span class="dgs-math-display">{svg}</span>' if display else svg


def compile_page(formulas: list[tuple[str, bool]], lang: str) -> list[tuple[str, tuple]]:
    """Every formula of one page in a single xelatex run. Returns (svg, metrics) in order."""
    CACHE.mkdir(parents=True, exist_ok=True)
    body = '\n'.join(
        r'\begin{dgsmath}' + (f'$\\displaystyle {tex}$' if display else f'${tex}$')
        + r'\end{dgsmath}'
        for tex, display in formulas)
    context = Context(content=body, lang=lang)
    source = StaticRenderer(TEMPLATE_ROOT).render(pathlib.Path(TEMPLATE), context.data)

    name = hashlib.sha1(source.encode()).hexdigest()[:32]
    tex = CACHE / f'{name}.tex'
    tex.write_text(source)
    subprocess.run(
        # no `-halt-on-error`: loading chemfig provokes a recoverable error inside MinionPro's
        # own `.fd`, and whether a PDF came out is the question that matters
        ['xelatex', '-interaction=nonstopmode', '-file-line-error', '-shell-escape',
         f'-output-directory={CACHE}', str(tex)],
        capture_output=True, text=True, check=False)

    pdf = CACHE / f'{name}.pdf'
    log = CACHE / f'{name}.log'
    if not pdf.is_file():
        complaint = ''
        if log.is_file():
            complaint = '\n'.join(line for line in log.read_text(errors='replace').splitlines()
                                  if line.startswith('!'))[:600]
        raise RenderError(f'xelatex would not set the page: {complaint}')

    metrics = [(float(h), float(d), float(x))
               for h, d, x in RE_METRIC.findall(log.read_text(errors='replace'))]
    if len(metrics) != len(formulas):
        raise RenderError(f'measured {len(metrics)} formulas of {len(formulas)}')

    converted = subprocess.run(
        ['dvisvgm', '--pdf', '--no-fonts', f'--page=1-{len(formulas)}',
         '-o', str(CACHE / f'{name}-%p.svg'), str(pdf)],
        capture_output=True, text=True, check=False)
    # `%p` is zero-padded to the width of the page count, so a 22-page run writes `-01`
    width = len(str(len(formulas)))
    out = []
    for index in range(1, len(formulas) + 1):
        piece = CACHE / f'{name}-{index:0{width}d}.svg'
        if not piece.is_file():
            raise RenderError(f'dvisvgm produced no page {index}: {converted.stderr[-400:]}')
        found = RE_SVG.search(piece.read_text())
        if not found:
            raise RenderError(f'no <svg> on page {index}')
        out.append((found.group(), metrics[index - 1]))
        piece.unlink()
    for suffix in ('.tex', '.pdf', '.log', '.aux'):
        (CACHE / f'{name}{suffix}').unlink(missing_ok=True)
    return out


def typeset(fragments: list[str], lang: str = 'sk') -> list[str]:
    """Every formula in every fragment of one page, replaced by its SVG."""
    wanted, places = {}, []
    for index, text in enumerate(fragments):
        for match in RE_MATH.finditer(text):
            latex = strip(match['body'])
            display = match['kind'] == 'display'
            key = digest(latex, lang, display)
            wanted.setdefault(key, (latex, display))
            places.append((index, match.span(), key))
    if not places:
        return list(fragments)

    CACHE.mkdir(parents=True, exist_ok=True)
    missing = [(key, value) for key, value in wanted.items()
               if not (CACHE / f'{key}.json').is_file()]
    if missing:
        for (key, _), (svg, metric) in zip(
                missing, compile_page([v for _, v in missing], lang), strict=True):
            (CACHE / f'{key}.json').write_text(json.dumps({'svg': svg, 'metric': metric}))

    out = list(fragments)
    for (index, (start, stop), key) in reversed(places):
        held = json.loads((CACHE / f'{key}.json').read_text())
        height, depth, exheight = held['metric']
        latex, display = wanted[key]
        out[index] = (out[index][:start]
                      + inline_svg(held['svg'], height, depth, exheight, display)
                      + out[index][stop:])
    return out
