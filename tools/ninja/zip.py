r"""
The tearoff archive: one PDF per language, each named after its language.

`output/…/languages/<lang>/tearoff.pdf` is what the build produces, and what a venue wants is an
archive of those under the names `sk.pdf`, `en.pdf` and so on. The Makefile did it by laying a
symlink beside each PDF and running `zip --junk-paths` over the links
(`modules/naboj/module.mk:548-551`), which leaves the links behind permanently -- `core/audit/stale.py`
carries a note about having to `unlink` rather than follow them -- and which **appends**, so a
language removed from the volume stayed in the archive for ever.

Writing the archive directly costs nothing and fixes both: no symlinks, and the file is replaced
rather than added to.
"""
import argparse
import pathlib
import sys
import zipfile


def language_of(pdf: pathlib.Path) -> str:
    """`output/naboj/phys/29/languages/sk/tearoff.pdf` → `sk`, from the directory it sits in."""
    return pdf.parent.name


def write(archive: pathlib.Path, pdfs: list[pathlib.Path]) -> int:
    archive.parent.mkdir(parents=True, exist_ok=True)
    # `w`, not `a`: the archive is the set of languages that exist now.
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
        for pdf in sorted(pdfs):
            out.write(pdf, f'{language_of(pdf)}.pdf')
    return len(pdfs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('archive', type=pathlib.Path)
    parser.add_argument('pdfs', type=pathlib.Path, nargs='+')
    args = parser.parse_args()
    print(f'{args.archive}: {write(args.archive, args.pdfs)} language(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
