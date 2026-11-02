r"""
Turn xelatex's `.fls` recorder log into a Ninja depfile.

**Why this is the right source.** Every other way of knowing what a document includes is a
guess. `\protectedInput` resolves its path against `\activeDirectory`, a macro set at run time by
`\setActive`, and then asks `\IfFileExists`; `\insertPicture` does the same. Nothing upstream can
predict the answer, which is why `modules/naboj/module.mk` falls back to depending on *directories*
(`naboj_problem_dirs`, `:114-132`) and on every `.jtex` in the tree at once. With `-recorder`,
TeX writes down what it actually opened, and the next build is told exactly that.

What is filtered out, and why:

- **Everything outside the repository.** TeX Live is some 1200 files per run -- fonts, `.fmt`,
  every `.sty` -- and none of it changes without a distribution upgrade, which is not an event
  this build should try to track. Keeping them would multiply the graph by two orders of
  magnitude for nothing.
- **The run's own outputs** (`.aux`, `.log`, `.out`, `.synctex.gz`, the `.pdf` itself). TeX reads
  its own `.aux` from the previous pass, and a depfile naming the target as its own dependency is
  a cycle Ninja refuses with `dependency cycle`.
- **`OUTPUT` lines.** Only `INPUT` is a dependency.

Usage, as the second half of a build command:

    xelatex -recorder … && python -m tools.ninja.fls out.fls out.pdf out.pdf.d
"""
import argparse
import pathlib
import sys

#: Produced by the run itself, so never a dependency of it.
OUTPUTS = {'.aux', '.log', '.out', '.pdf', '.synctex', '.gz', '.toc', '.nav', '.snm', '.fls'}


def dependencies(fls: pathlib.Path, repo: pathlib.Path, target: pathlib.Path) -> list[str]:
    """Every file inside the repository that this run read, once each, in a stable order."""
    seen, out = set(), []
    target = target.resolve()
    lines = fls.read_text(errors='replace').splitlines()
    # A relative INPUT is relative to the directory TeX ran in, which the log states on its
    # first line -- *not* to wherever the `.fls` itself landed. `-jobname` puts the log under
    # `output/…` while the run happens at the repository root, so resolving against the file's
    # own directory turns `build/core/i18n/sk.tex` into
    # `output/…/languages/sk/build/core/i18n/sk.tex`, a path that exists nowhere.
    base = fls.parent
    for line in lines:
        if line.startswith('PWD '):
            base = pathlib.Path(line[4:])
            break
    for line in lines:
        if not line.startswith('INPUT '):
            continue
        path = pathlib.Path(line[6:])
        if not path.is_absolute():
            path = base / path
        try:
            path = path.resolve()
            relative = path.relative_to(repo)
        except (ValueError, OSError):
            continue                    # outside the repository: TeX Live, and it does not move
        if path == target or path.suffix in OUTPUTS or path in seen:
            continue
        seen.add(path)
        out.append(str(relative))
    return sorted(out)


def write(fls: pathlib.Path, target: str, depfile: pathlib.Path, repo: pathlib.Path) -> int:
    deps = dependencies(fls, repo, pathlib.Path(target))
    # Ninja's depfile parser takes one target and a space-separated list; a space in a path is
    # escaped with a backslash, which is also how make spells it.
    escaped = ' '.join(d.replace(' ', r'\ ') for d in deps)
    depfile.write_text(f"{target}: {escaped}\n")
    return len(deps)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('fls', type=pathlib.Path)
    parser.add_argument('target')
    parser.add_argument('depfile', type=pathlib.Path)
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path('.'))
    args = parser.parse_args()
    if not args.fls.is_file():
        # No recorder log means the run did not get that far; an empty depfile is correct and
        # lets Ninja fall back to the declared inputs rather than failing on a missing file.
        args.depfile.write_text(f'{args.target}:\n')
        return 0
    write(args.fls, args.target, args.depfile, args.repo.resolve())
    return 0


if __name__ == '__main__':
    sys.exit(main())
