r"""
Whether a LaTeX document wants another pass, asked of the document itself.

Every document was compiled exactly twice, unconditionally, in both build systems -- the two
commands differ only in three `texfot --ignore` arguments, which filter stdout and never reach
TeX. That is right for a cold build and wasted for every other one, and xelatex is 71 % of the
work: 127 edges against 585 of the build's 819 edge-seconds.

LaTeX already says which it is. Measured on eight of volume 29's document kinds, a **cold** pass
with no `.aux` asks for a rerun in all eight, and a **warm** pass with the previous build's `.aux`
in place asks in none -- so a cold build keeps both passes and the authoring loop drops one.

The four requests a cold first pass actually emits here:

    Package hyperref Warning: Rerun to get /PageLabels entry.
    LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.
    (rerunfilecheck)                Rerun to get outlines right
    Package lastpage Warning: Rerun to get the references right on input line 293.

`Rerun to get` covers all four and is the whole matcher. **`Rerun` alone would not be**: every log
carries `Package: rerunfilecheck 2022-07-10 v1.10 Rerun checks for auxiliary files (HO)`, so a
matcher that naive fires on every document and the second pass is never skipped -- the failure
that looks like the feature not working rather than like a bug.

Line wrapping is not a hazard: the rules set `max_print_line=1000`, which applies to the log as
well as the terminal, so a warning is never split across lines.

Usage, in the middle of a build command:

    xelatex … && if python -m tools.ninja.rerun out.log; then xelatex … ; fi && …

Exit 0 means *run the second pass*, so that `if` reads the way it is spelled.
"""
import argparse
import pathlib
import sys

#: What a request for another pass looks like, in all four of its spellings.
REQUEST = 'Rerun to get'


def wanted(log: pathlib.Path) -> bool:
    """
    Whether this run asked to be repeated.

    **Unreadable means yes.** A missing log means the run did not get far enough to say, and the
    two mistakes are not symmetrical: a wrong "skip" ships a booklet with a stale cross-reference
    in it, and a wrong "rerun" costs two seconds.
    """
    try:
        return REQUEST in log.read_text(errors='replace')
    except OSError:
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('log', type=pathlib.Path)
    args = parser.parse_args()
    return 0 if wanted(args.log) else 1


if __name__ == '__main__':
    sys.exit(main())
