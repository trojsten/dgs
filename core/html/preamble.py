r"""
What the page's maths is set *by* -- the template and every file it `\input`s.

Two callers need the same list for two different reasons, and before this each had its own copy
of it:

- **`tools/ninja/generate.py`** declares these as implicit inputs of every `page` edge, so that
  editing `math.tex` rebuilds the pages. Its copy was a hand-written tuple in a different
  language in a different directory from the `\input` lines it was mirroring.
- **`core/html/texmath.py`** caches each rendered formula under a hash, and that hash has to
  move when the macros move, or the rebuild reassembles the page out of SVGs typeset by the old
  ones. Its copy of the question was a hand-bumped `VERSION = '3'`.

**Those two had drifted into a defect with no symptom.** The graph was right: touch
`core/latex/math.tex` and Ninja rebuilt all fifteen thousand pages. The cache was not: every one
of them came back out of `build/.html-math/` exactly as it had been typeset before the edit. A
green build, a correct-looking rebuild, and the wrong maths on the page -- invisible in both
directions, because a stale cache and a warm one are indistinguishable from the outside.

So the list is read off the template instead of written down, and the hash of its contents is
what the cache is keyed on. Hand-bumping a version number is the thing this removes: it is a
step somebody has to remember at exactly the moment they are thinking about something else.

Stdlib only, deliberately. `generate.py` imports this, and the generator has no business
dragging in jinja2 and pint to ask which files the maths preamble is made of.
"""
import functools
import hashlib
import os
import pathlib
import re

#: The checkout this module lives in, so that everything below is answered the same from any
#: working directory. It used to be the relative `core/templates`, which meant
#: `tools/ninja/generate.py --repo <elsewhere>` read a template root that was not the one it was
#: generating for: every `page` edge then got an empty `--files` and a single implicit input,
#: which is a build that dies in argparse and a preamble hash covering nothing.
ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = ROOT / 'core' / 'templates'
TEMPLATE = TEMPLATE_ROOT / 'mathpage.jtex'

#: `\input{core/latex/math.tex}`. The Jinja tags in the template are left alone -- the only one
#: in an `\input` is the i18n table, which is excluded below.
RE_INPUT = re.compile(r'\\input\{([^}]*)\}')

#: `(@ include 'standalone-preamble.jtex' @)`. The packages and the `\input` lines moved into
#: that file so `mathpage.jtex` and `standalone.jtex` could stop being two copies of them, which
#: means this scan has to follow one level in -- otherwise it would see a template with no
#: `\input`s at all and hash nothing that matters.
RE_INCLUDE = re.compile(r"\(@\s*include\s*'([^']+)'\s*@\)")


@functools.cache
def inputs() -> tuple[str, ...]:
    r"""
    The template, the templates it includes, and every static file those `\input`, in order.

    **`build/` paths are excluded**, which is one line and worth the sentence. The preamble's
    last `\input` is `build/core/i18n/(* lang *).tex` -- a generated file, named through a Jinja
    tag, different for every language. It is not part of what the preamble *is*; the language is
    already in the cache key, and the graph declares that file through the i18n edge that makes
    it. Hashing it here would mean reading a path that does not exist until something builds it.
    """
    found: list[str] = []
    for template in templates(TEMPLATE.name):
        found.append(template)
        text = (ROOT / template).read_text()
        found += [path for path in RE_INPUT.findall(text)
                  if not path.startswith('build/') and path not in found]
    return tuple(found)


@functools.cache
def templates(name: str) -> tuple[str, ...]:
    r"""
    One template under `core/templates/` and every template it `(@ include @)`s, repo-relative.

    Separate from `inputs()` because the two are needed at different stages. A **rendered
    `.tex`** depends on the Jinja chain and nothing else: the `\input` lines are still text at
    that point, resolved later by LaTeX. A **compiled PDF** depends on both, and gets the second
    half from xelatex's `-recorder` -- except on the page edge, which runs its xelatex inside
    `core/html/texmath.py` where there is no recorder to read, which is why `inputs()` exists.

    `tools/ninja/generate.py` uses this for the picture `.tex`, and it is a fix: moving the
    shared preamble out of `standalone.jtex` left that edge naming only `standalone.jtex`, so
    adding a package to the preamble rebuilt all 4399 pages and not one of the 1317 pictures.
    """
    out: list[str] = []
    pending = [name]
    while pending:
        current = pending.pop(0)
        relative = (TEMPLATE_ROOT / current).relative_to(ROOT).as_posix()
        if relative in out:
            continue
        out.append(relative)
        try:
            text = (TEMPLATE_ROOT / current).read_text()
        except OSError:
            continue
        pending += RE_INCLUDE.findall(text)
    return tuple(out)


def _key() -> tuple:
    """
    Every input's size and modification time -- what to notice a change by, cheaply.

    Six `stat` calls, against reading and hashing six files, on a function that is asked once
    per formula on a page. Cheap enough not to need caching of its own, and honest in a
    long-lived process: the editor serves for hours, and somebody editing `math.tex` while it
    runs should not have to restart it to see the formula change. That is the trap the `VERSION`
    constant set, and it is the same one `functools.cache` on a bare path would set again.
    """
    out = []
    for path in inputs():
        try:
            stat = os.stat(path)
        except OSError:
            out.append((path, None))
        else:
            out.append((path, stat.st_mtime_ns, stat.st_size))
    return tuple(out)


@functools.cache
def _digest_of(key: tuple) -> str:
    sha = hashlib.sha1()
    for path in inputs():
        try:
            sha.update(pathlib.Path(path).read_bytes())
        except OSError:
            # A missing input is the compile's failure to report, with the file named, rather
            # than this function's. Hash the name so the key still moves when it comes back.
            sha.update(path.encode())
        sha.update(b'\0')
    return sha.hexdigest()[:16]


def digest() -> str:
    """A hash of everything the maths preamble is made of. Recomputed only when one moves."""
    return _digest_of(_key())
