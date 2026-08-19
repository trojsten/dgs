"""
The audit checks that cost minutes rather than milliseconds: does it render, does it compile.

Kept apart from `core.audit.checks` because everything there is a file read and a regex, and this
shells out to make. Run one scope at a time, when asked, and cache the answer -- the source-only
layer can afford to recompute on every request and this cannot.
"""
import json
import re
import subprocess
import time
from pathlib import Path

#: `Overfull \hbox (12.34pt too wide)`, and the vbox form, which is a page overflowing rather than
#: a line. The size matters: a 0.14pt overfull is 0.05 mm and not worth anybody's afternoon.
RE_OVERFULL = re.compile(r'Overfull \\+(?P<box>[hv])box \((?P<size>[0-9.]+)pt too (?:wide|high)\)')
RE_ANSI = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b[()][A-Za-z0-9]')
RE_TEX_ERROR = re.compile(r'^(?P<file>\./[^:]+):(?P<line>\d+): (?P<message>.+)$', re.M)

#: What a naboj volume builds. Every module's targets differ, so this is a naboj fact; a module
#: that wants build checks says so by appearing here.
TARGETS = {'naboj': ('booklet', 'solutions', 'answers', 'tearoff')}

CACHE_DIR = Path('build') / '.audit'


def cache_path(repo_root: Path, module: str, scope: str) -> Path:
    return repo_root / CACHE_DIR / module / f"{scope.replace('/', '-')}.json"


def read_cache(repo_root: Path, module: str, scope: str):
    path = cache_path(repo_root, module, scope)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(repo_root: Path, module: str, scope: str, payload):
    path = cache_path(repo_root, module, scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False))


def languages_of(module_root: Path, scope: str):
    """The languages a scope publishes in, from its `languages/` directory."""
    root = module_root / scope / 'languages'
    if not root.is_dir():
        return []
    return sorted(child.name for child in root.iterdir() if child.is_dir())


def run_targets(repo_root: Path, module: str, scope: str, languages, targets, *,
                run, timeout=900):
    """
    Build every target of every language, collecting what came back.

    `run` is injected rather than called directly so the Flask app can pass its own make runner --
    the one that holds `BUILD_LOCK` and strips ANSI -- and so this is testable without a toolchain.
    """
    results = []
    for language in languages:
        for target in targets:
            make_target = f"output/{module}/{scope}/languages/{language}/{target}.pdf"
            outcome = run(make_target, timeout=timeout)
            log = RE_ANSI.sub('', outcome.get('log', ''))
            overfulls = sorted(
                ({'box': m['box'], 'size': float(m['size'])} for m in RE_OVERFULL.finditer(log)),
                key=lambda o: -o['size'])
            results.append({
                'language': language,
                'target': target,
                'ok': outcome.get('returncode', 1) == 0,
                # only the largest few: a booklet reports the same box once per xelatex pass
                'overfull': overfulls[:5],
                'errors': [f"{m['file']}:{m['line']}: {m['message']}"[:200]
                           for m in RE_TEX_ERROR.finditer(log)][:5],
            })
    return results


def audit_build(repo_root: Path, module_root: Path, module: str, scope: str, *,
                fingerprint, run):
    """Run the build checks for one scope and cache the outcome."""
    languages = languages_of(module_root, scope)
    targets = TARGETS.get(module, ())
    started = time.time()
    results = run_targets(repo_root, module, scope, languages, targets, run=run) \
        if languages and targets else []
    payload = {
        'scope': scope,
        'module': module,
        'ran_at': started,
        'duration': round(time.time() - started, 1),
        # so the page can say "sources have changed since this ran"
        'fingerprint': fingerprint,
        'languages': languages,
        'targets': list(targets),
        'results': results,
        'ok': sum(1 for r in results if r['ok']),
        'total': len(results),
    }
    write_cache(repo_root, module, scope, payload)
    return payload
