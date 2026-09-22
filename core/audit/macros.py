r"""
The one audit question that cannot be answered by reading files: is this macro defined at all?

`core/latex/math.tex` alone names 191 macros and `dgs.cls` loads 146 packages on top of it, which
shadow and complete each other -- `\Chi` turns out to come from `mathspec`, `\bigtimes` from
MnSymbol, `\sfrac` from xfrac by way of chemmacros. No amount of reading `core/latex/` settles
whether a given name exists. The only authority is TeX, so this asks it: one probe document that
runs `\ifcsname` over every control word in the tree and reports the ones nothing answers to.

It is worth asking because an undefined macro does not look like a defect in review. `scholar/TA1`
called `\diff` 222 times and `\OIInt` 22, `naboj/fks-naboj` called `\EvalAt` and `\integrate`, and
one FKS solution had carried a dead `\diff` row next to its live `\Diff` copy for years -- all of
it invisible, because nothing ever built those modules. The first person to run `make` on them
would have met `Undefined control sequence` in a file they did not write.

Kept out of `core.audit.checks` for the reason stated there: that layer is file reads and regexes
and costs a fifth of a second over the whole repository. This costs a xelatex run, so it caches
the way `core.audit.build` does, in `build/.audit/`, against a fingerprint of both halves -- the
macro definitions and the words found -- and reruns only when one of them moves.
`checks.macro_undefined` reads the cache and places the findings.
"""
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import yaml

#: This file is `<repo>/core/audit/macros.py`.
REPO_ROOT = Path(__file__).resolve().parents[2]

CACHE = Path('build') / '.audit' / 'macros.json'
PROBE = Path('build') / '.audit' / 'macro-probe.tex'

#: A control word: a backslash and two or more letters. One letter is `\,`, `\!`, `\ ` and the
#: other spacing primitives, plus `\\` -- all of them built in, none of them ever the question.
RE_CONTROL_WORD = re.compile(r'\\([A-Za-z]{2,})')

#: What the probe writes for a name nothing answers to. Chosen not to look like a TeX message.
RE_REPORTED = re.compile(r'^DGSUNDEF: ([A-Za-z]+)$', re.MULTILINE)

#: Names the probe calls undefined that are nothing of the sort, and why. `\ifcsname` asks about
#: the global table, and chemfig defines these two only inside a `\schemestart` group, where they
#: are the only place they are ever written.
IGNORED = {
    'arrow': 'chemfig defines it inside \\schemestart only',
    'schemestop': 'chemfig defines it inside \\schemestart only',
}

#: The files whose definitions decide the answer. `dgs.cls` names the packages; the rest is ours.
DEFINITIONS = ('core/latex/dgs.cls', 'core/latex')


def words_in(text: str) -> set:
    """Every control word in a piece of LaTeX."""
    return set(RE_CONTROL_WORD.findall(text))


def _yaml_words(path: Path) -> set:
    """
    Control words in a meta, read from the *parsed* strings rather than the raw bytes.

    A double-quoted YAML scalar has escapes of its own: `"Agata\\tStefa\\u0144ska"` holds a tab and
    a Unicode codepoint, and reading it raw offers TeX a `\\tStefa` that no author ever wrote. The
    parser has already spent them, so what comes back is only what will reach the renderer.
    """
    try:
        data = yaml.safe_load(path.read_text())
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        return set()
    found = set()

    def walk(node):
        if isinstance(node, str):
            found.update(words_in(node))
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(key)
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(data)
    return found


def collect(source_root: Path) -> set:
    """Every control word the sources use, from markdown verbatim and from metas once parsed."""
    found = set()
    seen = set()
    for path in sorted(source_root.rglob('*')):
        if not path.is_file():
            continue
        real = path.resolve()                   # 84 symlinks under source/; read each file once
        if real in seen:
            continue
        seen.add(real)
        if path.suffix == '.md':
            try:
                found |= words_in(path.read_text())
            except (OSError, UnicodeDecodeError):
                continue
        elif path.name.endswith('.yaml'):
            found |= _yaml_words(path)
    return found


def probe_source(names) -> str:
    r"""A document that asks `\ifcsname` about each name and says nothing about the ones that are."""
    body = '\n'.join(rf'\ifcsname {name}\endcsname\else\typeout{{DGSUNDEF: {name}}}\fi'
                     for name in sorted(names))
    return f"\\documentclass[12pt]{{dgs}}\n\\begin{{document}}\n{body}\nx\n\\end{{document}}\n"


def run_xelatex(repo_root: Path, path: Path) -> str:
    """
    Compile the probe and hand back its log.

    From the repository root, because `dgs.cls` reaches its pieces by relative path and
    `~/texmf/tex/latex/dgs.cls` is a symlink into the tree, so the class asked is this working copy.
    """
    subprocess.run(
        ['xelatex', '-interaction=nonstopmode', f'-output-directory={path.parent}', str(path)],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    log = path.with_suffix('.log')
    return log.read_text(errors='replace') if log.is_file() else ''


def fingerprint(repo_root: Path, names) -> str:
    """
    Both halves of the question: what is defined, and what is asked.

    A new macro in `core/latex/` can answer an old complaint, and a new source can raise a new one,
    so a digest of one alone would go stale silently in the other direction.
    """
    h = hashlib.sha1()
    for entry in DEFINITIONS:
        target = repo_root / entry
        for f in sorted(target.rglob('*')) if target.is_dir() else [target]:
            if f.is_file():
                h.update(f.name.encode())
                h.update(f.read_bytes())
    h.update('\n'.join(sorted(names)).encode())
    return h.hexdigest()


def sweep(repo_root: Path = REPO_ROOT, *, source_root: Path = None, run=run_xelatex) -> dict:
    """Ask TeX about every control word in the tree, and cache the answer."""
    names = collect(source_root or repo_root / 'source')
    started = time.time()
    probe = repo_root / PROBE
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(probe_source(names))
    log = run(repo_root, probe)
    reported = {name for name in RE_REPORTED.findall(log)} - set(IGNORED)
    payload = {
        'ran_at': started,
        'duration': round(time.time() - started, 1),
        'fingerprint': fingerprint(repo_root, names),
        'asked': len(names),
        'undefined': sorted(reported),
        'ignored': IGNORED,
    }
    cache = repo_root / CACHE
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    return payload


def read_cache(repo_root: Path = REPO_ROOT) -> dict | None:
    path = repo_root / CACHE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def undefined_names(repo_root: Path = REPO_ROOT) -> frozenset:
    """
    What the last sweep found, or nothing at all if it has never run.

    Nothing rather than a guess, deliberately: the source-only layer must not invent findings out
    of an answer it has not got. A page that wants to say "this has not been checked" reads
    `read_cache()` and sees `None`.
    """
    payload = read_cache(repo_root)
    return frozenset(payload['undefined']) if payload else frozenset()


def is_stale(repo_root: Path = REPO_ROOT, *, source_root: Path = None) -> bool | None:
    """True when the sources or the definitions have moved since the sweep; None if it never ran."""
    payload = read_cache(repo_root)
    if payload is None:
        return None
    names = collect(source_root or repo_root / 'source')
    return payload.get('fingerprint') != fingerprint(repo_root, names)


def main():
    """`python -m core.audit.macros` -- the sweep from a terminal, for CI or a quick answer."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--check', action='store_true',
                        help='read the cache instead of running; exit 1 if it is stale or absent')
    args = parser.parse_args()

    if args.check:
        payload, stale = read_cache(), is_stale()
        if payload is None:
            print('the macro sweep has never run')
            raise SystemExit(1)
        if stale:
            print('the macro sweep is stale: sources or definitions have moved since it ran')
            raise SystemExit(1)
    else:
        payload = sweep()

    undefined = payload['undefined']
    print(f"{payload['asked']} control words asked, {len(undefined)} undefined")
    for name in undefined:
        print(f"  \\{name}")
    raise SystemExit(1 if undefined else 0)


if __name__ == '__main__':
    main()
