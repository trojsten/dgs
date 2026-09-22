r"""
The only test coverage `core/latex/` has.

`core/latex/math.tex` defines 191 public macros and, until this file existed, nothing exercised
them: a fault surfaced only when an author happened to reach for the broken macro. Five of them
were broken -- `\OIntC` and `\Laplacian` expanded `physics` macros that `dgs.cls` does not load,
`\LXor` and `\LNand` expanded control sequences no package in the tree defines,
`\CartesianProductP` was missing a bracket -- and `\SmallO` set nothing at all, which is the
case that matters most: `\mathcal{o}` is not a compile error. xelatex writes
`Missing character:` into the log and carries on, so the compile stays green and the page comes
out with a hole in it.

Hence two assertions on every run, not one: the exit status *and* the log.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LATEX = ROOT / 'core' / 'tests' / 'latex'
OUTPUT = ROOT / 'build' / '.tests'

#: A `Missing character` line means a glyph the font has not got; xelatex does not consider it an
#: error. `Undefined control sequence` reaches here only when `-halt-on-error` did not fire first.
SILENT_FAILURES = re.compile(r'Missing character|Undefined control sequence')

#: Names that cannot be exercised standalone, and why. Empty today -- `\Operation` needs an
#: alignment and gets one inside the probe's `aligned` block. Add an entry rather than dropping a
#: macro from the probe, so that the omission is deliberate and says why.
EXCLUDED: dict[str, str] = {}

DEFINITION = re.compile(
    r'\\(?:New|Renew|Provide)DocumentCommand\s*\{\\([A-Za-z@]+)\}'
    r'|\\newcommand\*?\s*\\([A-Za-z@]+)'
    r'|\\DeclareMathOperator\s*\{\\([A-Za-z@]+)\}'
    r'|\\DeclareMathSymbol\s*\{\\([A-Za-z@]+)\}'
    r'|\\DeclarePairedDelimiter\s*\{\\([A-Za-z@]+)\}'
)


def public_macros(source: Path) -> set[str]:
    """Every name the file defines that a document may use -- so, no `@` in it."""
    found = set()
    for match in DEFINITION.finditer(source.read_text()):
        name = next(group for group in match.groups() if group)
        if '@' not in name:
            found.add(name)
    return found


def compile_latex(stem: str) -> tuple[int, str]:
    """
    Run xelatex on `core/tests/latex/<stem>.tex` and return its status and log.

    From the repository root, because `dgs.cls` reaches its pieces by relative path
    (`\\input{core/latex/math.tex}`) and `~/texmf/tex/latex/dgs.cls` is a symlink to the one in
    the tree, so the class under test is always this working copy.
    """
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ['xelatex', '-halt-on-error', '-interaction=nonstopmode',
         f'-output-directory={OUTPUT}', f'core/tests/latex/{stem}.tex'],
        cwd=ROOT, capture_output=True, text=True,
    )
    log = (OUTPUT / f'{stem}.log').read_text(errors='replace')
    return result.returncode, log


@pytest.fixture(scope='module')
def probe() -> tuple[int, str]:
    return compile_latex('probe')


class TestProbe:
    def test_it_compiles(self, probe):
        status, log = probe
        assert status == 0, f"xelatex failed:\n{log[-3000:]}"

    def test_it_sets_every_glyph(self, probe):
        """
        The half that a zero exit status does not cover.

        `\\SmallO` was `\\mathcal{o}` and the calligraphic alphabet has no lowercase, so the
        macro printed nothing and the build stayed green.
        """
        _status, log = probe
        silent = sorted({line.strip() for line in log.splitlines() if SILENT_FAILURES.search(line)})
        assert not silent, "the log reports a failure the exit status did not:\n" + '\n'.join(silent)

    def test_it_uses_every_public_macro(self):
        """
        A macro added to `math.tex` without a line in the probe is never compiled by anything.

        That is exactly how the five broken ones survived: all of them had zero uses in
        `source/` as well, so no document ever expanded them.
        """
        defined = public_macros(ROOT / 'core' / 'latex' / 'math.tex')
        used = set(re.findall(r'\\([A-Za-z]+)', (LATEX / 'probe.tex').read_text()))
        missing = sorted(defined - used - set(EXCLUDED))
        assert not missing, \
            f"not exercised by core/tests/latex/probe.tex: {missing}. " \
            f"Add a line there, or an EXCLUDED entry saying why it cannot stand alone."


class TestRetiredSyntax:
    def test_diff_bracket_still_stops_the_build(self):
        """
        `\\Diff[2]{x}` must fail loudly.

        Without the `t[` guard it sets `\\Delta[2]x` -- the bracket becomes part of the formula
        and the power silently vanishes, which is the outcome the guard exists to rule out.
        """
        status, log = compile_latex('diff-bracket')
        assert status != 0, "the retired [power] form compiled instead of erroring"
        assert 'does not take a bracketed argument' in log, f"wrong error:\n{log[-2000:]}"
