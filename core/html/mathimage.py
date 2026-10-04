r"""
The escape hatch: maths that MathJax cannot do, rendered by the TeX that makes the booklet.

Most maths reaches the web as maths -- MathJax handles ordinary LaTeX, it has an mhchem
extension for `\ce`, and `core/filters/siunitx.lua` deals with the units. What is left is the
material that is not really maths at all: **chemfig**, which is TikZ wearing a chemical hat, 84
times in `chem/01` alone and with no web implementation of any kind.

For those, the answer is not to approximate. `core/templates/standalone.jtex` already loads
`math.tex`, `siunitx.tex`, `symbols.tex`, mhchem, chemmacros *and* chemfig, and `build/%.svg`
already turns a PDF into an SVG, so the picture a browser gets is made by the same LaTeX that
makes the printed one and cannot differ from it.

It is cached by the hash of what went in, under `build/.html-math/`, because the alternative is
an xelatex run per fragment per build.
"""
from __future__ import annotations

import hashlib
import io
import pathlib
import shutil
import subprocess

from core.builder.standalone import BuilderStandalone

#: Where the rendered fragments live. Content-addressed, so a fragment that has not changed is
#: not re-rendered and two problems writing the same formula share one file.
CACHE = pathlib.Path('build/.html-math')

#: Bumped when anything that changes the *appearance* changes -- the wrapper, the macros, the
#: dvisvgm invocation. The hash covers the fragment and the language; it cannot see those.
VERSION = '1'


class RenderError(RuntimeError):
    """LaTeX would not compile the fragment. The message carries the log's complaint."""


def digest(latex: str, lang: str) -> str:
    """
    The cache name, which `core/filters/texmath.lua` computes identically so that the common
    case -- the fragment is already rendered -- costs a file test rather than a Python process.

    SHA-1 because that is the hash pandoc's Lua offers (`pandoc.utils.sha1`), and this is a
    cache key rather than anything that has to resist an adversary.
    """
    return hashlib.sha1(f'{VERSION}\0{lang}\0{latex}'.encode()).hexdigest()[:32]


def wrap(latex: str, lang: str) -> str:
    """The fragment inside `standalone.jtex`, which is what a `.tikz` picture gets too."""
    out = io.StringIO()
    BuilderStandalone(lang, io.StringIO(latex), out)
    return out.getvalue()


def render(latex: str, lang: str, *, cache: pathlib.Path = CACHE) -> pathlib.Path:
    """
    The fragment as an SVG, from the cache or freshly compiled.

    Runs from the repository root, because `standalone.jtex` reaches for `core/latex/*.tex` and
    `build/core/i18n/<lang>.tex` by relative path exactly as the `.tikz` rule does.
    """
    name = digest(latex, lang)
    svg = cache / f'{name}.svg'
    if svg.is_file():
        return svg

    cache.mkdir(parents=True, exist_ok=True)
    tex = cache / f'{name}.tex'
    tex.write_text(wrap(latex, lang))

    compiled = subprocess.run(
        # No `-halt-on-error`, unlike the picture rules. Loading chemfig and chemmacros
        # provokes a recoverable `Undefined control sequence` inside MinionPro's own `.fd`,
        # which `nonstopmode` steps over and which halting turns into a failed build for a
        # fragment that otherwise compiles perfectly. Whether a PDF came out is the better
        # question, and it is the one asked below.
        ['xelatex', '-interaction=nonstopmode', '-file-line-error',
         '-shell-escape', f'-output-directory={cache}', str(tex)],
        capture_output=True, text=True, check=False,
    )
    # Whether a PDF came out, and not what xelatex returned: in `nonstopmode` it exits nonzero
    # after an error it has already stepped over, and the MinionPro `.fd` quirk chemfig provokes
    # is one of those -- `Output written on ….pdf (1 page)` in the same run that exits 1.
    pdf = cache / f'{name}.pdf'
    if not pdf.is_file():
        log = cache / f'{name}.log'
        complaint = ''
        if log.is_file():
            complaint = '\n'.join(line for line in log.read_text(errors='replace').splitlines()
                                  if line.startswith('!') or '.tex:' in line)[:600]
        raise RenderError(f'could not compile a maths fragment:\n{complaint or compiled.stdout[-600:]}')

    converted = subprocess.run(['dvisvgm', '--pdf', '--no-fonts', '-o', str(svg), str(pdf)],
                               capture_output=True, text=True, check=False)
    if converted.returncode != 0 or not svg.is_file():
        raise RenderError(f'dvisvgm would not convert the fragment:\n{converted.stderr[-600:]}')

    # the intermediates are not interesting once the SVG exists, and they are per-fragment
    for suffix in ('.tex', '.pdf', '.log', '.aux'):
        (cache / f'{name}{suffix}').unlink(missing_ok=True)
    return svg


def main() -> int:
    """`python -m core.html.mathimage <lang>`, LaTeX on stdin, the SVG's path on stdout."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('lang')
    args = parser.parse_args()
    if not shutil.which('xelatex'):
        print('xelatex is not on the path', file=sys.stderr)
        return 1
    try:
        print(render(sys.stdin.read(), args.lang))
    except RenderError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
