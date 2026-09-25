"""
Assert this machine has exactly the tiers named on the command line, and no others.

`capabilities.main()` exits 0 only when *every* tier is available. That is the right question for
a workstation and the wrong one for an image that is deliberately not supposed to have all of
them: for the `light` container image `pdf` absent is the **correct** answer, and its exit code 1
is indistinguishable from a broken pandoc.

The property an image wants is an exact profile -- these tiers and no others -- because both
directions are defects. A `light` image that lost pandoc is broken; a `light` image that quietly
grew a TeX distribution is broken too, just more expensively.

    python tools/editor/expect-tiers.py markdown tex             # the light image
    python tools/editor/expect-tiers.py markdown tex latex pdf   # the full image

Both images run this as a build step, so a broken one cannot be tagged.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capabilities                                            # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def check(expected, repo_root=ROOT):
    """Returns (exit code, lines to print). Separated so a test can call it."""
    report = capabilities.capabilities(repo_root, refresh=True)
    known = {tier['id'] for tier in report['tiers']}
    wanted = set(expected)

    if not wanted:
        return 2, ['expect-tiers.py: name at least one tier, e.g. markdown tex']
    if unknown := sorted(wanted - known):
        return 2, [f'no such tier: {", ".join(unknown)}',
                   f'known tiers: {", ".join(sorted(known))}']

    lines = [f'  {t["label"]:20} {"available" if t["ok"] else "UNAVAILABLE"}'
             + ('' if t['ok'] else f'   {t["reason"]}')
             for t in report['tiers']]

    available = {tier['id'] for tier in report['tiers'] if tier['ok']}
    if available == wanted:
        return 0, lines
    if missing := sorted(wanted - available):
        lines.append(f'\nexpected but missing: {", ".join(missing)}')
    if extra := sorted(available - wanted):
        lines.append(f'\npresent but not expected: {", ".join(extra)}')
    return 1, lines


def main(argv):
    code, lines = check(argv)
    stream = sys.stdout if code == 0 else sys.stderr
    for line in lines:
        print(line, file=stream)
    return code


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
