r"""
Remove what `make` cannot: built directories whose source has been renamed or deleted.

`Makefile:55-61` explains why this has to be a separate pass -- a target whose prerequisite has
vanished has no rule left to remove it, and `.SECONDARY:` keeps every intermediate -- so a
renamed problem leaves its `render/` and `build/` copies behind for ever. Usually that is dead
weight; it is a wrong page when the volume meta still names the unit, because `\protectedInput`
finds the stale `.tex` and prints the deleted problem.

`core/audit/stale.py` decides what counts, and the audit's `build-orphan` reports the same thing
on the `/audit` page. This is the half that acts.

It **lists and exits** unless `--delete` is given, because the alternative is a tool that removes
things when you meant to ask it a question.

It lives in `tools/` rather than in `core/audit/` for one reason: finding every scope means
reading the module descriptors, and `tools/editor/descriptors.py` is where that already happens.
`core/` does not import `tools/`, and should not start.
"""
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'tools' / 'editor'))

# After the path setup above, which is what makes both of these importable: `core` from the
# repository root, `descriptors` from `tools/editor`, where module discovery already lives.
from descriptors import audited_modules, discover_scopes, load_modules

from core.audit import stale
from core.audit.sources import read_scope


def find(repo_root: Path):
    """Every orphan in the repository, module by module and scope by scope."""
    found = []
    for module in audited_modules(load_modules(repo_root)):
        for scope, units in sorted(discover_scopes(module).items()):
            # The module's own file families are not passed, and need not be: `orphans` reads
            # unit *directories*, so which markdown files a unit may hold never comes into it.
            sources = read_scope(module.root, module.name, scope, units)
            found += [(module.name, orphan) for orphan in stale.orphans(sources)]
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--delete', action='store_true',
                        help='actually remove them; without this it only lists')
    args = parser.parse_args()

    found = find(REPO_ROOT)
    if not found:
        print('nothing stale under build/ or render/')
        return

    files = sum(orphan.files for _, orphan in found)
    for module, orphan in found:
        print(f'  {module:<8} {orphan}  ({orphan.files} files)')
        if args.delete:
            stale.remove(orphan)

    verb = 'removed' if args.delete else 'stale (run with --delete to remove)'
    print(f'{len(found)} director{"y" if len(found) == 1 else "ies"}, {files} files {verb}')


if __name__ == '__main__':
    main()
