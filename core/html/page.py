r"""
Fragments into a page a browser can open.

`build/…/<problem>/<lang>/{problem,solution,answer}.html` are pandoc fragments: no `<head>`, no
stylesheet, no MathJax. This puts one problem's fragments into `core/templates/page.jhtml`, which
is the HTML analogue of `booklet.jtex` -- and, like the booklet, it is where the pieces are
*arranged*, not where they are rendered.

Pictures move with it. A fragment says `![](rollercoaster.svg)` because that is what the author
wrote next to the problem; the page says `<img src="pictures/rollercoaster.svg">` and the picture
is copied in beside it, so the directory works from `file://` with nothing else present.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys

from core import i18n
from core.builder.context import Context
from core.builder.jinja import StaticRenderer

TEMPLATE_ROOT = pathlib.Path('core/templates')
TEMPLATE = 'page.jhtml'
#: Where a page keeps the pictures it points at, relative to itself.
PICTURES = 'pictures'
#: And the maths engine, copied in rather than linked up the tree.
#:
#: Firefox gives every `file://` document its own origin, so a page cannot load a script from a
#: sibling directory: `../../../core/html/vendor/…` is blocked, MathJax never starts, and the
#: page shows `\(1.8\,\mathrm{m}\)` as text. Online it looked fine, because MathJax was
#: quietly fetching its font from the CDN -- which is the opposite of what vendoring is for.
MATHJAX = 'mathjax'
VENDOR = pathlib.Path('core/html/vendor')
#: One file with the font baked in, plus mhchem and the glyph chunks.
#:
#: The *combined* build and not `tex-svg-nofont.js` plus a font package, because MathJax fetches
#: a separate font package dynamically and Firefox gives every `file://` document its own
#: origin, so the fetch is blocked and nothing typesets. Online it hid: MathJax fell through to
#: the CDN and the page looked right, which is the opposite of what vendoring is for.
RUNTIME = ('mathjax/tex-mml-svg-mathjax-pagella.js', 'mathjax/input',
           'mathjax/svg', 'mathjax/LICENSE')

RE_IMG = re.compile(r'(<img[^>]*\ssrc=")(?P<src>[^"]*)(")')


def collect(fragment: pathlib.Path, *, sources: list[pathlib.Path],
            destination: pathlib.Path) -> str:
    """
    One fragment, with every picture it names copied next to the page and the `src` repointed.

    A picture can be beside the problem (`build/…/<problem>/x.svg`), inside the language
    directory, or in the shared maths cache (`build/.html-math/…`) if LaTeX drew it. All three
    end up in one `pictures/` directory, because a page that only works from the repository root
    is not a page anybody can send to anyone.
    """
    text = fragment.read_text()
    missing = []

    def repoint(match):
        src = pathlib.Path(match['src'])
        for root in sources:
            candidate = root / src
            if candidate.is_file():
                target = destination / PICTURES / src.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, target)
                return f'{match.group(1)}{PICTURES}/{src.name}{match.group(3)}'
        if src.is_file():                               # already a path from the repository root
            target = destination / PICTURES / src.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
            return f'{match.group(1)}{PICTURES}/{src.name}{match.group(3)}'
        missing.append(str(src))
        return match.group(0)

    out = RE_IMG.sub(repoint, text)
    if missing:
        raise FileNotFoundError(f'{fragment}: no such picture: {", ".join(missing)}')
    return out


def install_runtime(destination: pathlib.Path) -> None:
    """MathJax and its font, beside the page, because `file://` will not reach outside."""
    for item in RUNTIME:
        source = VENDOR / item
        target = destination / MATHJAX / item
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        elif source.is_file():
            shutil.copyfile(source, target)


def build(problem: pathlib.Path, lang: str, destination: pathlib.Path, *,
          title: str | None = None, files=('problem', 'solution', 'answer')) -> pathlib.Path:
    """Assemble `<problem>/<lang>/*.html` into `<destination>/index.html`."""
    sources = [problem / lang, problem, pathlib.Path('.')]
    destination.mkdir(parents=True, exist_ok=True)

    pieces = []
    for name in files:
        fragment = problem / lang / f'{name}.html'
        if not fragment.is_file():
            continue
        pieces.append(f'<section class="{name}">')
        pieces.append(collect(fragment, sources=sources, destination=destination))
        pieces.append('</section>')
    if not pieces:
        raise FileNotFoundError(f'{problem}/{lang}: no fragments to assemble')

    install_runtime(destination)
    context = Context(
        content='\n'.join(pieces),
        lang=lang,
        title=title or problem.name,
        mathjax=MATHJAX,
        # inlined rather than linked, for the same `file://` reason as the engine
        css=pathlib.Path('core/html/page.css').read_text(),
    )
    page = destination / 'index.html'
    page.write_text(StaticRenderer(TEMPLATE_ROOT).render(pathlib.Path(TEMPLATE), context.data))
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('problem', type=pathlib.Path,
                        help='a built problem directory under build/')
    parser.add_argument('lang', choices=sorted(i18n.languages))
    parser.add_argument('destination', type=pathlib.Path)
    parser.add_argument('--title')
    args = parser.parse_args()
    print(build(args.problem, args.lang, args.destination, title=args.title))
    return 0


if __name__ == '__main__':
    sys.exit(main())
