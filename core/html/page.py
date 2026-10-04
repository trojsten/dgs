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
from html import escape

from core import html, i18n
from core.builder.context import Context
from core.builder.jinja import StaticRenderer
from core.html import mathjax, texmath
from tools.editor import descriptors

TEMPLATE_ROOT = pathlib.Path('core/templates')
TEMPLATE = 'page.jhtml'


RE_IMG_WHOLE = re.compile(r'<img(?P<before>[^>]*?)\ssrc="(?P<src>[^"]*)"(?P<after>[^>]*)>')
RE_STYLE = re.compile(r'\sstyle="(?P<style>[^"]*)"')


#: How much of the window a picture may never take, so it cannot push the page sideways.
#: `100vw` counts the scrollbar in every engine, which is most of this gutter's job.
GUTTER = 'calc(100vw - 2rem)'

#: `width:40mm` / `height:60mm` as pandoc writes them from `{height=60mm}`.
RE_LENGTH = re.compile(r'\b(?P<axis>width|height)\s*:\s*(?P<value>[0-9.]+)mm')
#: The opening `<svg …>`, whose `width`/`height`/`viewBox` give the drawing's proportions.
RE_SVG_OPEN = re.compile(r'<svg\b[^>]*>', re.DOTALL)
RE_SVG_ATTR = re.compile(r'\b(width|height|viewBox)\s*=\s*["\']([^"\']*)["\']')
#: A length with a unit, as an SVG writes one: `432pt`, `576`, `11cm`.
RE_SVG_LENGTH = re.compile(r'^\s*([0-9.]+)\s*([a-z%]*)\s*$')


def aspect(picture: pathlib.Path) -> float | None:
    """
    Width over height, or None when the format is one we do not read.

    Needed because the authored size is a **height** and the web has to be told a **width**:
    see `size`. Read from the file rather than from a table, so a redrawn picture resizes
    itself.
    """
    suffix = picture.suffix.lower()
    try:
        if suffix == '.svg':
            opening = RE_SVG_OPEN.search(picture.read_text(errors='replace'))
            if not opening:
                return None
            attributes = dict(RE_SVG_ATTR.findall(opening.group()))
            width, height = attributes.get('width'), attributes.get('height')
            if width and height:
                pair = [RE_SVG_LENGTH.match(value) for value in (width, height)]
                # a percentage is relative to something we do not have; fall through to viewBox
                if all(pair) and not any(m.group(2) == '%' for m in pair):
                    return float(pair[0].group(1)) / float(pair[1].group(1))
            box = (attributes.get('viewBox') or '').replace(',', ' ').split()
            if len(box) == 4 and float(box[3]):
                return float(box[2]) / float(box[3])
            return None
        if suffix == '.png':
            raw = picture.read_bytes()[:33]
            if raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
                return None
            width = int.from_bytes(raw[16:20], 'big')
            height = int.from_bytes(raw[20:24], 'big')
            return width / height if height else None
        if suffix in ('.jpg', '.jpeg'):
            return _jpeg_aspect(picture.read_bytes())
    except (OSError, ValueError, ZeroDivisionError):
        return None
    return None


def _jpeg_aspect(raw: bytes) -> float | None:
    """The first SOF marker's dimensions. JPEG has no header to read, only a chain of segments."""
    at = 2
    while at + 9 < len(raw) and raw[at] == 0xFF:
        marker, length = raw[at + 1], int.from_bytes(raw[at + 2:at + 4], 'big')
        # SOF0..SOF15, less the four that are not frame headers
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC, 0xD8):
            height = int.from_bytes(raw[at + 5:at + 7], 'big')
            width = int.from_bytes(raw[at + 7:at + 9], 'big')
            return width / height if height else None
        at += 2 + length
    return None


def size(style: str, picture: pathlib.Path) -> str:
    r"""
    The authored print size, as a web page can honour it.

    `{height=30mm}` is a height, and LaTeX is told `width=\linewidth, height=30mm,
    keepaspectratio` -- fit the measure, be at most 30mm tall. A web page cannot be told a
    bare height either: on a 4:1 drawing 30mm of height asks for 46.5mm of a page whose width
    nobody knows. Said as a **width** it says both at once, and the picture's own proportions
    are what convert the one into the other -- which is why this happens here, with the file
    in hand, and not in the convertor.

    **The limit is the window, not the measure.** The booklet clamps a drawing to `\linewidth`
    because a page has an edge; a page that scrolls has not, so the authored height is honoured
    and a wide drawing is let past the text column -- `29/chopper` is 4:1 and asks for 60mm of
    height, which is 240mm of width, more than the 180mm the booklet can give it. The
    stylesheet centres such a picture on the window; this only says how wide it may be.

    It used to be `max-height: 30mm; height: auto`, a ceiling rather than a size, and that is
    why every drawing was too small: a ceiling only ever binds when the picture is *larger*
    than asked for, and an SVG's intrinsic size is whatever its producer wrote -- `29/chopper`
    is 432x108pt, so it showed 38mm tall.
    """
    lengths = {m['axis']: float(m['value']) for m in RE_LENGTH.finditer(style)}
    width = lengths.get('width')
    if width is None and 'height' in lengths:
        ratio = aspect(picture)
        if ratio:
            width = lengths['height'] * ratio
    if width is None:
        # no width we can compute: a ceiling is at least never wrong, only sometimes small
        ceiling = f'max-height: {lengths["height"]:g}mm; ' if 'height' in lengths else ''
        return f'max-width: {GUTTER}; {ceiling}height: auto'
    return f'width: min({width:.1f}mm, {GUTTER}); height: auto'


class MissingPictures(FileNotFoundError):
    """
    Pictures a page names and has not got. Carries the page, which **was still written**.

    The same shape as the renderer's missing-word registry, for the same reason: one absent
    drawing should not cost you the other six problems of the round, and whoever is fixing it
    wants the whole page with the holes marked. So the gap is boxed in place, every one is
    collected, the page is written, and only then does the build go red -- the box is not the
    safety net, the nonzero exit is.
    """

    def __init__(self, page: pathlib.Path, missing: list[str]):
        self.page, self.missing = page, missing
        super().__init__(f'{page}: no such picture: {", ".join(missing)}')


def collect(fragment: pathlib.Path, *, sources: list[pathlib.Path],
            destination: pathlib.Path, missing: list[str]) -> str:
    """
    One fragment, with every picture it names copied next to the page and the `src` repointed.

    A picture can be beside the problem (`build/…/<problem>/x.svg`) or inside the language
    directory; either way it is copied next to the page under its own name, so the `src` the
    author wrote keeps working and the directory can be sent to anyone as it stands.

    A picture that is nowhere becomes a red box naming it, and is recorded for the caller.
    """
    text = fragment.read_text()

    def repoint(match):
        src = pathlib.Path(match['src'])
        for root in (*sources, pathlib.Path('.')):
            candidate = root / src
            if candidate.is_file():
                target = destination / src.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, target)
                rest = match['before'] + match['after']
                styled = RE_STYLE.search(rest)
                sized = size(styled['style'] if styled else '', target)
                # pandoc closes the tag `… />`; the slash would otherwise land mid-attribute
                rest = RE_STYLE.sub('', rest).rstrip().removesuffix('/').rstrip()
                return f'<img{rest} src="{src.name}" style="{sized}">'
        missing.append(str(src))
        return (f'<span class="dgs-missing">Missing picture: '
                f'{escape(str(src))}</span>')

    return RE_IMG_WHOLE.sub(repoint, text)


#: How to set the maths, by name. See `core/html/__init__.py` for what each one costs.
ENGINES = {'latex': texmath.typeset, 'mathjax': mathjax.typeset}


def describe(module: str):
    """
    What `modules/<module>/editor.yaml` says this module's units hold.

    Read rather than guessed, and read from the file that already says it: `languages: true`
    is Náboj's, and seminar's descriptor does not carry it because **seminar is monolingual**
    -- one language, not one of several that happens to be checked out. That is a fact about
    the module, so it belongs to the module, the way `equation_numbering` and `audit: true` do.
    """
    modules = descriptors.load_modules(pathlib.Path('.'))
    if module not in modules:
        raise ValueError(
            f'no such module: {module} -- '
            f'`modules/{module}/editor.yaml` is missing, or `source/{module}/` is not checked '
            f'out. Known: {", ".join(sorted(modules)) or "none"}')
    described = modules[module]
    # Every target any of this module's unit kinds may hold, in the order they are declared.
    # scholar has four kinds and the union is harmless: a fragment that does not exist is
    # skipped, so the list only has to be complete and in a sensible order.
    targets = list(dict.fromkeys(target
                                 for kind in described.kinds for target in kind.targets))
    return described.languages, targets


def build(problem: pathlib.Path, lang: str, destination: pathlib.Path, *,
          title: str | None = None, files=None, engine: str | None = None,
          module: str | None = None) -> pathlib.Path:
    """
    Assemble one unit's fragments into `<destination>/index.html`.

    Where those fragments are is the module's to say. Náboj puts a directory per language
    inside a problem, so a fragment is `<problem>/<lang>/solution.html`; seminar is
    monolingual and its fragments sit in `<problem>/` directly. `lang` is still wanted either
    way -- it picks the i18n and the babel the maths is set with, which a one-language module
    has as much as a six-language one.
    """
    engine = engine or html.ENGINE
    if engine not in ENGINES:
        raise ValueError(f'no such maths engine: {engine} (try {", ".join(ENGINES)})')

    # `build/<module>/…`, the same rule `core/markdown-check.py` infers a module by
    module = module or (problem.parts[1] if len(problem.parts) > 1 else '')
    languages, targets = describe(module)
    directory = problem / lang if languages else problem

    sources = [directory, problem]
    destination.mkdir(parents=True, exist_ok=True)

    bodies, names, missing = [], [], []
    for name in files if files is not None else targets:
        fragment = directory / f'{name}.html'
        if not fragment.is_file():
            continue
        names.append(name)
        bodies.append(collect(fragment, sources=sources, destination=destination,
                              missing=missing))
    if not bodies:
        raise FileNotFoundError(f'{directory}: no fragments to assemble')

    # The maths is typeset here, once, so the page carries finished SVG and needs no
    # JavaScript. The fragments are engine-neutral -- they hold the formula the author wrote --
    # so either engine can set the same build, and the choice costs a page rebuild and nothing
    # upstream of it.
    bodies = ENGINES[engine](bodies, lang)
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
    if missing:
        raise MissingPictures(page, missing)
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('problem', type=pathlib.Path,
                        help='a built problem directory under build/')
    parser.add_argument('lang', choices=sorted(i18n.languages))
    parser.add_argument('destination', type=pathlib.Path)
    parser.add_argument('--title')
    parser.add_argument('--module', help='which module this unit belongs to; inferred from the '
                                         'path (`build/<module>/…`) when not given')
    parser.add_argument('--maths', choices=sorted(ENGINES), default=html.ENGINE,
                        help='how to set the maths: `latex` makes a picture of each formula with '
                             'the xelatex that sets the booklet, exact and in MinionPro; '
                             '`mathjax` makes selectable text in Pagella, through the shims')
    args = parser.parse_args()
    try:
        print(build(args.problem, args.lang, args.destination,
                    title=args.title, engine=args.maths, module=args.module))
    except MissingPictures as gap:
        # the page is written and carries a box per hole; the build still goes red
        print(gap.page)
        print(f'{len(gap.missing)} picture(s) missing: {", ".join(gap.missing)}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
