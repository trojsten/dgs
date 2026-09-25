"""
What this machine can actually do, so the editor can say so instead of failing.

The pipeline is three stages and the editor's tabs are those three stages: `render/…md` is
Jinja and needs nothing but Python; `build/…tex` adds pandoc; `output/…pdf` adds the whole TeX
stack and the fonts. A machine that has only the first is still useful to a translator, and this
module is what lets the app know that rather than shelling out and reporting whatever make printed.

Nothing here may raise because a tool is absent -- that is the entire point of it -- so every
probe goes through `_run`, which swallows `FileNotFoundError` and a timeout and returns `None`.

Run it on its own for a plain-text report:

    uv run python tools/editor/capabilities.py
"""
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

# One place for install text, quoting the repository's own scripts rather than inventing
# commands that would drift from them.
INSTALL = {
    'make': ['sudo apt install make'],
    'uv': ['curl -LsSf https://astral.sh/uv/install.sh | sh'],
    'python': ['uv sync --dev', '# or activate the venv you installed into'],
    'pandoc': ['./install-pandoc.sh', 'export PATH="$HOME/.local/bin:$PATH"'],
    'pandoc-crossref': ['./install-pandoc.sh', 'export PATH="$HOME/.local/bin:$PATH"'],
    'xelatex': ['sudo apt install texlive-full texlive-fonts-extra texlive-science'],
    'texfot': ['sudo apt install texlive-full'],
    'dgs.cls': ['ln -s "$PWD/core/latex/dgs.cls" "$(kpsewhich -var-value=TEXMFHOME)/tex/latex/dgs.cls"'],
    'MinionPro.sty': [
        'sudo apt install lcdf-typetools',
        'git clone https://github.com/sebschub/FontPro assets/fonts/FontPro',
        'cd assets/fonts/FontPro && mkdir -p otf && cp ../MinionPro/*.otf otf/',
        './scripts/makeall MinionPro && sudo ./scripts/install',
        'updmap-user --enable Map=MinionPro.map',
    ],
    'gnuplot': ['sudo apt install gnuplot'],
    'rsvg-convert': ['sudo apt install librsvg2-bin'],
}


@dataclass(frozen=True)
class Tool:
    name: str
    found: bool
    path: str = ''
    version: str = ''
    #: found, and still does not count -- a mismatched pandoc pair, a `dgs.cls` from another clone
    detail: str = ''

    @property
    def install(self):
        return INSTALL.get(self.name, [])


@dataclass(frozen=True)
class Tier:
    id: str
    label: str
    ok: bool
    missing: tuple = ()
    reason: str = ''
    install: tuple = ()


def _which(name):
    return shutil.which(name) or ''


def _run(argv, *, stdin=None, timeout=30):
    """Every probe goes through here. Returns (returncode, stdout+stderr), or None if absent."""
    try:
        done = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    return done.returncode, (done.stdout or '') + (done.stderr or '')


# --- individual probes -------------------------------------------------------


def probe_make():
    """
    BSD make accepts the invocation and then misparses `.SECONDEXPANSION`, which every rule in
    this repository leans on, so finding *a* make is not enough.
    """
    path = _which('make')
    if not path:
        return Tool('make', False)
    result = _run(['make', '--version'], timeout=10)
    first = result[1].splitlines()[0] if result and result[1] else ''
    if 'GNU Make' not in first:
        return Tool('make', False, path, first, 'found, but it is not GNU make')
    return Tool('make', True, path, first)


def probe_python_launcher():
    """
    How `run_make` should invoke make, and why `uv` is not required.

    `uv` is only there to put the project's interpreter on PATH for the Makefile's bare `python`
    in `define jinja` and `define _pandoc`. This process *is* such an interpreter -- it imported
    jinja2, yaml and all of core.audit to get here -- so when uv is absent we call make directly
    with our own interpreter's directory prepended to PATH. In a venv that directory holds the
    `python` the recipes call.
    """
    # Deliberately NOT resolve()d: a venv's `bin/python` is a symlink to the base interpreter,
    # so resolving it lands in /usr/local/bin and loses the venv -- which is the one directory
    # that matters, because that is where the dependencies are importable from.
    bindir = str(Path(sys.executable).parent)
    if _which('uv'):
        return {'argv': ['uv', 'run', 'make'], 'via': 'uv', 'path_prefix': '',
                'note': ''}
    if (Path(bindir) / 'python').exists():
        return {'argv': ['make'], 'via': 'python', 'path_prefix': bindir,
                'note': f'uv is not installed; running make with {bindir} on PATH'}
    return {'argv': ['make'], 'via': 'none', 'path_prefix': bindir,
            'note': ('uv is not installed and there is no `python` beside this interpreter, so '
                     "the Makefile's recipes will not find one")}


def probe_pandoc():
    """
    pandoc and pandoc-crossref, probed *functionally* -- which is not optional here.

    `install-pandoc.sh` deliberately symlinks the filter into pandoc's user data directory,
    which `--filter` consults ahead of PATH, so a perfectly good install can have nothing named
    `pandoc-crossref` on PATH at all. And a version mismatch between the two only warns on
    stderr and builds green, which is the failure the installer's own check exists to catch. So
    we run the same check it does: one document through the filter, and look at what comes back.
    """
    path = _which('pandoc')
    if not path:
        return Tool('pandoc', False), Tool('pandoc-crossref', False)

    version = ''
    result = _run(['pandoc', '--version'], timeout=10)
    if result and result[0] == 0:
        match = re.match(r'pandoc\s+([0-9.]+)', result[1])
        version = match.group(1) if match else ''
    pandoc = Tool('pandoc', True, path, version)

    probe = 'x [-@eq:d]\n\n$$E=mc^2$$ {#eq:d}\n'
    result = _run(['pandoc', '--from', 'markdown+smart', '--to', 'latex',
                   '--filter', 'pandoc-crossref'], stdin=probe, timeout=30)
    if result is None:
        return pandoc, Tool('pandoc-crossref', False, detail='pandoc could not be run')
    code, output = result
    if code != 0:
        return pandoc, Tool('pandoc-crossref', False, detail=_first_line(output))
    if 'WARNING' in output:
        return pandoc, Tool('pandoc-crossref', False, _which('pandoc-crossref'),
                            detail=('the filter and pandoc are a mismatched pair -- '
                                    + _first_line(output)))
    if 'ref{eq:d}' not in output:
        return pandoc, Tool('pandoc-crossref', False, _which('pandoc-crossref'),
                            detail='the filter ran but did not resolve a reference')
    return pandoc, Tool('pandoc-crossref', True, _which('pandoc-crossref') or '(pandoc data dir)')


def probe_latex(repo_root):
    """
    xelatex on PATH does not promise a PDF: `dgs.cls` has to be reachable through kpsewhich and
    `MinionPro.sty` has to exist, which means somebody ran the FontPro build.
    """
    tools = [Tool('xelatex', bool(_which('xelatex')), _which('xelatex')),
             Tool('texfot', bool(_which('texfot')), _which('texfot'))]

    for name in ('dgs.cls', 'MinionPro.sty'):
        result = _run(['kpsewhich', name], timeout=10)
        found = bool(result and result[0] == 0 and result[1].strip())
        where = result[1].strip().splitlines()[0] if found else ''
        detail = ''
        if found and name == 'dgs.cls':
            # install.sh symlinks $PWD/core/latex/dgs.cls into TEXMFHOME, so with two clones on
            # one machine TeX silently uses the other one's class. Worth saying even when green.
            ours = (repo_root / 'core' / 'latex' / 'dgs.cls').resolve()
            try:
                if Path(where).resolve() != ours:
                    detail = f'resolves to {where}, which is not this clone'
            except OSError:
                pass
        tools.append(Tool(name, found, where, detail=detail))
    return tools


def probe_advisories():
    """Needed only by a unit that has a figure, so never a gate -- but worth naming."""
    return [Tool(name, bool(_which(name)), _which(name))
            for name in ('gnuplot', 'rsvg-convert', 'dvisvgm', 'pdfcrop')]


def _first_line(text):
    for line in (text or '').splitlines():
        if line.strip():
            return line.strip()
    return ''


# --- tiers -------------------------------------------------------------------


def _tier(ident, label, tools, needed, extra_reason=''):
    missing = [t.name for t in tools if t.name in needed and not t.found]
    if not missing:
        return Tier(ident, label, True)
    reasons = [f'{t.name}: {t.detail}' for t in tools if t.name in missing and t.detail]
    reason = '; '.join(reasons) or f"{', '.join(missing)} not found"
    if extra_reason:
        reason = f'{reason}. {extra_reason}'
    install = []
    for name in missing:
        for line in INSTALL.get(name, []):
            if line not in install:      # pandoc and its filter share a script; say it once
                install.append(line)
    return Tier(ident, label, False, tuple(missing), reason, tuple(install))


def capabilities(repo_root, *, refresh=False):
    """The whole picture, as plain dicts ready for `jsonify`."""
    repo_root = Path(repo_root)
    with _LOCK:
        if _CACHE.get('payload') is not None and not refresh:
            return _CACHE['payload']

        launcher = probe_python_launcher()
        make = probe_make()
        pandoc, crossref = probe_pandoc()
        latex = probe_latex(repo_root)
        advisories = probe_advisories()

        python_ok = launcher['via'] != 'none'
        floor = [make, Tool('python', python_ok, sys.executable, detail=launcher['note'])]
        tools = floor + [pandoc, crossref] + latex

        markdown = _tier('markdown', 'Rendered Markdown', tools, {'make', 'python'})
        # What it takes to compile a `.tex` -- no pandoc. The macro sweep needs exactly this and
        # nothing more: it writes its own probe document and hands it straight to xelatex.
        latex = _tier('latex', 'LaTeX', tools,
                      {'xelatex', 'texfot', 'dgs.cls', 'MinionPro.sty'})
        tex = _tier('tex', 'TeX', tools, {'make', 'python', 'pandoc', 'pandoc-crossref'})
        pdf = _tier('pdf', 'PDF', tools,
                    {'make', 'python', 'pandoc', 'pandoc-crossref',
                     'xelatex', 'texfot', 'dgs.cls', 'MinionPro.sty'})

        # A tier is never usable when the one below it is not, whatever its own tools say.
        if not markdown.ok:
            tex = Tier('tex', 'TeX', False, markdown.missing, markdown.reason, markdown.install)
            pdf = Tier('pdf', 'PDF', False, markdown.missing, markdown.reason, markdown.install)
        elif not tex.ok:
            pdf = Tier('pdf', 'PDF', False, tex.missing, tex.reason, tex.install)

        payload = {
            'tools': {t.name: dict(asdict(t), install=t.install) for t in tools},
            'tiers': [asdict(t) for t in (markdown, tex, latex, pdf)],
            'advisories': [dict(asdict(t), install=t.install) for t in advisories if not t.found],
            'launcher': launcher,
        }
        _CACHE['payload'] = payload
        return payload


_CACHE = {'payload': None}
_LOCK = threading.Lock()


def tier(repo_root, ident):
    """One tier, as a `Tier`, for the routes that need to refuse."""
    for entry in capabilities(repo_root)['tiers']:
        if entry['id'] == ident:
            return Tier(**entry)
    raise KeyError(ident)


def main():
    root = Path(__file__).resolve().parents[2]
    report = capabilities(root, refresh=True)
    print(f'DGS toolchain in {root}\n')
    for name, t in report['tools'].items():
        mark = 'yes' if t['found'] else 'NO '
        line = f'  {mark}  {name:16} {t["path"] or ""}'
        print(line.rstrip())
        if t['detail']:
            print(f'            {t["detail"]}')
    print()
    for t in report['tiers']:
        mark = 'available' if t['ok'] else 'UNAVAILABLE'
        print(f'  {t["label"]:20} {mark}')
        if not t['ok']:
            print(f'      {t["reason"]}')
            for line in t['install']:
                print(f'      $ {line}')
    if report['advisories']:
        print('\n  figures may not build without:')
        for t in report['advisories']:
            print(f'      {t["name"]}')
    if report['launcher']['note']:
        print(f'\n  {report["launcher"]["note"]}')
    return 0 if all(t['ok'] for t in report['tiers']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
