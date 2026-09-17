"""
Moving a finished draft into the tree.

`draft.py` writes drafts and refuses to write anywhere near `source/`, which is the right
default: a draft is re-run constantly and would clobber hand-finishing. This is the other
half -- the one step that *does* write into `source/naboj/phys/<volume>/`, and it only does
so when the draft has stopped being a draft.

**The gates, and why each one is here rather than in a reviewer's head:**

- **Every problem is named.** Provisional ids must never reach the tree: renaming one later
  means moving a directory and rewriting every `#fig:` and `#eq:` label inside it. This is
  `convert.py`'s rule and it is not negotiable.
- **No `%# TODO` survives.** `tools/ancient/README.md`: the conversion is not finished while
  one remains.
- **No formula is still a hole.** A `⟨math⟩` marker means the decode could not read it.
- **Every problem has a solution.** A stub solution renders as a red `Missing file` box, and
  volume 19 shipped one of those on page 42 for years without anyone noticing.
- **Nothing is overwritten.** A problem directory that already exists is left alone unless
  `--force` is given, because `phys/02` already holds three hand-made problems that came from
  the same booklet and must not be flattened by a machine.

A volume that fails any gate is reported in full and nothing is written. Partial promotion is
worse than none: it leaves a tree that looks converted and is not.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import yaml

#: What a slug must look like, matching what every volume in the tree already uses.
RE_SLUG = re.compile(r'^[a-z][a-z0-9-]*$')

#: The markers `draft.py` leaves behind when it could not finish something.
RE_UNFINISHED = re.compile(r'%# TODO|⟨math⟩')


def _problems(draft: Path) -> list[str]:
    return sorted(p.name for p in (draft / 'problems').iterdir() if p.is_dir())


def check(draft: Path, slugs: dict[str, str], target: Path,
          force: bool = False, incomplete: bool = False) -> list[str]:
    """
    Everything wrong with promoting this draft, in the order a person would fix it.

    `incomplete` waives the gates about *quality* -- unnamed problems, surviving `%# TODO`
    markers, unread formulas, missing solutions -- which is defensible on a working branch
    where the tree itself is the review surface. It does **not** waive the gate about
    overwriting: a half-finished decode may land next to hand-made work, never on top of it.
    """
    problems = _problems(draft)
    complaints: list[str] = []

    if not problems:
        return ['the draft holds no problems']

    for pid in problems:
        slug = slugs.get(pid)
        if slug is None and incomplete:
            pass                    # the provisional id stands in; see `promote`
        elif slug is None:
            complaints.append(f'{pid}: not named in the slug table')
        elif not RE_SLUG.match(slug):
            complaints.append(f'{pid}: `{slug}` is not a valid slug')
        elif (target / 'problems' / slug).exists() and not force:
            complaints.append(f'{pid} -> {slug}: already exists in the tree')

        if incomplete:
            continue
        for f in sorted((draft / 'problems' / pid).rglob('*.md')):
            text = f.read_text()
            if (m := RE_UNFINISHED.search(text)):
                where = f.relative_to(draft / 'problems')
                complaints.append(f'{pid}: {where} still contains `{m.group(0)}`')
                break

    seen: dict[str, str] = {}
    for pid in problems:
        if (slug := slugs.get(pid)) and slug in seen:
            complaints.append(f'{pid} and {seen[slug]} both claim the slug `{slug}`')
        elif slug:
            seen[slug] = pid
    return complaints


def promote(draft: Path, target: Path, slugs: dict[str, str],
            force: bool = False, dry_run: bool = False,
            incomplete: bool = False) -> list[str]:
    """
    Copy a checked draft into the tree, under its real names.

    Returns what it did, or what stopped it. The volume's `problems:` list is written in
    printed order -- position in that list *is* the running order, and it is what the build
    iterates, so a problem missing from it is never built at all.
    """
    if (complaints := check(draft, slugs, target, force, incomplete)):
        return ['refusing to promote:', *(f'  {c}' for c in complaints)]

    problems = _problems(draft)
    slugs = {pid: slugs.get(pid, pid) for pid in problems}
    done = []
    for pid in problems:
        src, dst = draft / 'problems' / pid, target / 'problems' / slugs[pid]
        if not dry_run:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        done.append(f'{pid} -> {slugs[pid]}')

    order = [slugs[pid] for pid in problems]
    if not dry_run and (meta := target / 'meta.yaml').is_file():
        meta.write_text(_splice_order(meta.read_text(), order))
    return [f'promoted {len(done)} problems into {target}', *(f'  {d}' for d in done)]


#: The `problems:` block and nothing else -- either `[]` or a list of `- item` lines.
RE_ORDER = re.compile(r'(?m)^problems:[ \t]*(?:\[\s*\]|(?:\n[ \t]*-[ \t].*)*)[ \t]*$')


def _splice_order(text: str, order: list[str]) -> str:
    """
    Replace the `problems:` list in a meta, leaving every other byte alone.

    Emphatically **not** `yaml.safe_dump`. Round-tripping a meta through PyYAML discards every
    comment in it and normalises the scalars -- which here meant losing the note that the date
    is a placeholder, the note that the start time is borrowed, and the warning that `11:00`
    is written unquoted because YAML 1.1 reads it as sexagesimal 660. In these volumes the
    comments *are* the provenance, and the provenance is most of the value.
    """
    block = 'problems:\n' + ''.join(f'  - {slug}\n' for slug in order)
    if RE_ORDER.search(text):
        return RE_ORDER.sub(block.rstrip('\n'), text, count=1)
    return text.rstrip('\n') + '\n\n' + block


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('draft', type=Path, help='the volume directory `draft.py` wrote')
    ap.add_argument('-t', '--target', type=Path, required=True,
                    help='source/naboj/phys/<volume>')
    ap.add_argument('-s', '--slugs', type=Path,
                    help='YAML mapping provisional id -> slug; optional with --incomplete')
    ap.add_argument('--force', action='store_true', help='overwrite problems already there')
    ap.add_argument('--incomplete', action='store_true',
                    help='waive the quality gates; keeps the overwrite protection')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    slugs = yaml.safe_load(a.slugs.read_text()) if a.slugs and a.slugs.is_file() else {}
    print('\n'.join(promote(a.draft, a.target, slugs or {}, a.force, a.dry_run,
                             a.incomplete)))


if __name__ == '__main__':
    main()
