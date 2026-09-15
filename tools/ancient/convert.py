r"""
Convert a year of the old Náboj TeX archive into a DGS volume — as a draft, for finishing by hand.

    uv run python -m tools.ancient.convert --year 2009 --volume 12 \
        --ancient source/naboj/fks-naboj/.ancient/2009/ulohy \
        --slugs   tools/ancient/slugs/2009.yaml \
        --out     /tmp/draft/12

It **never writes into `source/`**. The draft goes to `--out`, and moving it into the tree is a
separate, visible step; hand-finishing in the real tree can therefore never be clobbered by a
re-run. Review a re-run with `diff -ru <out>/problems/<pid> source/naboj/phys/<vol>/problems/<pid>`.

`--dry-run` writes only the report, which is how you point it at the next year and find out what
the rule table is missing before committing to it.
"""
import argparse
import re
import shutil
from pathlib import Path

import yaml

from tools.ancient import rules
from tools.ancient.dialect import Dialect
from tools.ancient.lex import calls, macro_body, strip_comments


def order(ancient: Path) -> list[str]:
    """The running order: `priklady.tex`, whose line positions were the problem numbers."""
    text = (ancient / 'priklady.tex').read_text(encoding='utf-8', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return [m.group(1).strip()
            for m in re.finditer(r'^[^%\n]*\\priklad\{\s*(.*?)\s*\}', text, re.M)]


def figures(text: str, dialect: Dialect, slug: str) -> tuple[str, list[str], list[str]]:
    r"""
    `\obrazok`/`\pict`/`\includegraphics` -> `![](x.svg){#fig:slug height=…}`.

    Returns the rewritten text, the figure stems wanted, and notes. The height is always
    reported: it is a visual choice and the old `scale` does not carry over.
    """
    notes, wanted = [], []

    def markdown(path: str, caption: str = '') -> str:
        stem = Path(path.strip()).stem
        # The archive names a figure after the Slovak problem and whether it belongs to the
        # statement (`_zad`) or the solution (`_ries`). The modern layout does not encode that
        # in the filename, so the figure takes the slug's name.
        if stem.endswith('_zad'):
            name = slug
        elif stem.endswith('_ries'):
            name = f'{slug}-solution'
        else:
            name = re.sub(r'[^a-z0-9-]+', '-', stem.lower()).strip('-')
        wanted.append((stem, name))
        notes.append(f'figure: `{name}.svg` -- set a real height, 40mm is a placeholder')
        return f'![{caption.strip()}]({name}.svg){{#fig:{slug} height=40mm}}'

    for name, arity in ((('obrazok'), dialect.figure_arity), ('pict', 2)):
        while True:
            found = list(calls(text, name, arity))
            if not found:
                break
            start, end, args = found[0]
            cap = args[dialect.figure_caption] if (name == 'obrazok'
                                                   and dialect.figure_caption is not None) else ''
            path = args[dialect.figure_file if name == 'obrazok' else 1]
            text = text[:start] + markdown(path, cap) + text[end:]

    while True:
        m = re.search(r'\\includegraphics(?:\[[^\]]*\])?\s*(?=\{)', text)
        if not m:
            break
        from tools.ancient.lex import match_brace
        e = match_brace(text, m.end())
        text = text[:m.start()] + markdown(text[m.end() + 1:e - 1]) + text[e:]

    text = re.sub(r'\\begin\{center\}\s*|\s*\\end\{center\}', '', text)
    return text, wanted, notes


def convert_body(text: str, dialect: Dialect, slug: str,
                 label: bool = False) -> tuple[str, list[str], list[str]]:
    """One `\\zadanie`/`\\vzorak`/`\\comment` body, through the whole table."""
    notes = list(dict.fromkeys(rules.report_only(text)))
    text, wanted, fig_notes = figures(text, dialect, slug)
    notes += fig_notes
    text = rules.expand_unit_macros(text, dialect)
    text, unit_notes = rules.quantities(text)
    notes += unit_notes
    text = rules.over_to_frac(text)
    for pattern, replacement in rules.SHORTHAND + rules.LINTED:
        text = pattern.sub(replacement, text)
    text = rules.markup(text)
    text = rules.ties(text)
    text = rules.operator_spaces(text)
    text, display_notes = rules.displays(text, slug if label else None)
    notes += display_notes
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    text = re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'
    return text, wanted, notes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--year', type=int, required=True)
    p.add_argument('--volume', type=int, required=True)
    p.add_argument('--ancient', type=Path, required=True)
    p.add_argument('--slugs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--only', help='one source path, e.g. TAZ/kornutok.tex')
    p.add_argument('--dry-run', action='store_true', help='write the report and nothing else')
    a = p.parse_args()

    dialect = Dialect.read(a.ancient, a.year)
    slugs = yaml.safe_load(a.slugs.read_text())
    sources = order(a.ancient)
    report = [f'# {a.year} -> volume {a.volume:02d}\n',
              f'{len(sources)} problems in `priklady.tex`.\n']
    total = 0

    for number, rel in enumerate(sources, 1):
        if a.only and rel != a.only:
            continue
        slug = slugs.get(rel)
        if not slug:
            report.append(f'\n## {number}. `{rel}` -- **no slug**, skipped\n')
            continue
        raw = strip_comments((a.ancient / rel).read_text(encoding='utf-8', errors='replace'))
        out = a.out / 'problems' / slug
        notes, wanted = [], []
        pieces = {}
        for macro, target in (('zadanie', 'sk/problem.md'),
                              ('vzorak', 'sk/solution.md'),
                              ('comment', 'answer.md')):
            body = macro_body(raw, macro)
            if body is None:
                notes.append(f'{macro}: absent from the source')
                continue
            converted, w, n = convert_body(body, dialect, slug, label=(macro == 'vzorak'))
            pieces[target] = (converted, list(n))
            wanted += w
            notes += [f'{macro}: {x}' for x in n]

        solution, answer = pieces.get('sk/solution.md'), pieces.get('answer.md')
        if solution and answer and solution[0] == answer[0]:
            note = 'identical to the comment -- this problem has no model solution'
            notes.append(f'vzorak: {note}')
            pieces['sk/solution.md'][1].append(note)
        if answer:
            note = ("`\\comment{}` is the evaluator's note, not an expression -- reduce it to the "
                    'answer and keep the marking guidance as a `%#` comment at the head of the '
                    'solution')
            notes.append(f'answer: {note}')
            answer[1].append(note)

        total += len(notes)
        report.append(f'\n## {number}. `{rel}` -> `{slug}`\n')
        report += [f'- {n}\n' for n in notes] or ['- nothing to decide\n']

        if a.dry_run:
            continue
        for target, (body, own) in pieces.items():
            path = out / target
            path.parent.mkdir(parents=True, exist_ok=True)
            header = ''.join(f'%# TODO({n})\n' for n in own)
            path.write_text(header + body, encoding='utf-8')
        for stem, name in dict.fromkeys(wanted):
            for svg in a.ancient.rglob(f'{stem}.svg'):
                shutil.copy(svg, out / f'{name}.svg')
                break
            else:
                report.append(f'- figure: no `{stem}.svg` anywhere under {a.ancient}\n')

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'report.md').write_text(''.join(report), encoding='utf-8')
    print(f'{len([s for s in sources if not a.only or s == a.only])} problem(s); '
          f'{total} thing(s) to decide; report at {a.out / "report.md"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
