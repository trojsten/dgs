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
from core.html import mathjax

TEMPLATE_ROOT = pathlib.Path('core/templates')
TEMPLATE = 'page.jhtml'
#: Where a page keeps the pictures it points at, relative to itself.
PICTURES = 'pictures'


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


def build(problem: pathlib.Path, lang: str, destination: pathlib.Path, *,
          title: str | None = None, files=('problem', 'solution', 'answer')) -> pathlib.Path:
    """Assemble `<problem>/<lang>/*.html` into `<destination>/index.html`."""
    sources = [problem / lang, problem, pathlib.Path('.')]
    destination.mkdir(parents=True, exist_ok=True)

    bodies, names = [], []
    for name in files:
        fragment = problem / lang / f'{name}.html'
        if not fragment.is_file():
            continue
        names.append(name)
        bodies.append(collect(fragment, sources=sources, destination=destination))
    if not bodies:
        raise FileNotFoundError(f'{problem}/{lang}: no fragments to assemble')

    # the maths is typeset here, once, so the page carries finished SVG and needs no JavaScript
    bodies = mathjax.typeset(bodies)
    pieces = [piece
              for name, body in zip(names, bodies, strict=True)
              for piece in (f'<section class="{name}">', body, '</section>')]
    context = Context(
        content='\n'.join(pieces),
        lang=lang,
        title=title or problem.name,
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
