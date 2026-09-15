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
import subprocess
from pathlib import Path

import yaml

from tools.ancient import figures as svgfix
from tools.ancient import rules
from tools.ancient.dialect import Dialect
from tools.ancient.lex import calls, macro_body, strip_comments


def order(ancient: Path) -> list[str]:
    """The running order: `priklady.tex`, whose line positions were the problem numbers."""
    text = (ancient / 'priklady.tex').read_text(encoding='utf-8', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return [m.group(1).strip()
            for m in re.finditer(r'^[^%\n]*\\priklad\{\s*(.*?)\s*\}', text, re.M)]


#: Slovak letters that carry a diacritic, and what they are underneath. A slug is ASCII.
FOLD = str.maketrans('áäčďéěíĺľňóôöŕřšťúůüýžÁÄČĎÉĚÍĹĽŇÓÔÖŔŘŠŤÚŮÜÝŽ',
                     'aacdeeillnooorrstuuuyzAACDEEILLNOOORRSTUUUYZ')


def provisional(rel: str) -> str:
    """
    A stand-in slug: the Slovak stem, folded to ASCII. Only ever for `--dry-run`.

    It exists so a report covers every problem instead of skipping them for want of a name.
    Naming is a separate sitting -- a slug has to read in English and be unique across every
    volume of every competition -- and these are neither.
    """
    stem = Path(rel).stem.translate(FOLD)
    return re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')


def figures(text: str, dialect: Dialect, slug: str,
            source_stem: str = '') -> tuple[str, list[str], list[str]]:
    r"""
    `\obrazok`/`\pict`/`\includegraphics` -> `![](x.svg){#fig:slug height=…}`.

    Returns the rewritten text, the figure stems wanted, and notes. The height is always
    reported: it is a visual choice and the old `scale` does not carry over.
    """
    notes, wanted = [], []
    #: The year's own `\label{}` -> the `#fig:` label it became, so `\ref{}` can be rewritten.
    labels: dict[str, str] = {}

    def markdown(path: str, caption: str = '', tag: str = '') -> str:
        stem = Path(path.strip()).stem
        # The archive names a figure after the Slovak problem and whether it belongs to the
        # statement (`_zad`) or the solution (`_ries`). The modern layout does not encode that
        # in the filename, so the figure takes the slug's name.
        # `_zad` is the statement's figure and `_ries` the solution's, each optionally
        # numbered or lettered when a problem has more than one: 2010 writes `korytko_ries1`,
        # `korytko_ries2`, `den_ries_a`. Matching only the bare suffixes left seven figures
        # named after their Slovak stem.
        part = re.match(r'^(?P<body>.*?)[-_](?:o[-_])?(?P<which>zad|ries)[-_]?'
                        r'(?P<index>[0-9A-Za-z]*)$', stem)
        if part:
            name = slug if part['which'] == 'zad' else f'{slug}-solution'
            if part['index']:
                name = f'{name}-{part["index"].lower()}'
            label = slug if name == slug else f'{slug}:{name[len(slug) + 1:]}'
        elif re.sub(r'_o$', '', stem) == source_stem:
            # A figure named after the problem and nothing else is its statement's: 2012's
            # `DYN/kopce.eps` belongs to `DYN/kopce.tex` and carries no `_zad`.
            name = label = slug
        else:
            name = re.sub(r'[^a-z0-9-]+', '-', stem.lower()).strip('-')
            label = f'{slug}:{name}'
        wanted.append((stem, name))
        if tag:
            labels[tag.strip()] = label
        notes.append(f'figure: `{name}.svg` -- set a real height, 40mm is a placeholder')
        # `#fig:<id>` or `#fig:<id>:<name>`, and nothing else: `markdown-check`'s `lfn` rule
        # rejects a label that does not open with the problem's own id.
        return f'![{caption.strip()}]({name}.svg){{#fig:{label} height=40mm}}'

    for name, arity in ((('obrazok'), dialect.figure_arity), ('pict', 2)):
        while True:
            found = list(calls(text, name, arity))
            if not found:
                break
            start, end, args = found[0]
            cap = args[dialect.figure_caption] if (name == 'obrazok'
                                                   and dialect.figure_caption is not None) else ''
            tag = args[dialect.figure_label] if (name == 'obrazok'
                                                 and dialect.figure_label is not None) else ''
            path = args[dialect.figure_file if name == 'obrazok' else 1]
            text = text[:start] + markdown(path, cap, tag) + text[end:]

    while True:
        m = re.search(r'\\includegraphics(?:\[[^\]]*\])?\s*(?=\{)', text)
        if not m:
            break
        from tools.ancient.lex import match_brace
        e = match_brace(text, m.end())
        text = text[:m.start()] + markdown(text[m.end() + 1:e - 1]) + text[e:]

    text = re.sub(r'\\begin\{center\}\s*|\s*\\end\{center\}', '', text)

    # `\ref{zemA}` -> `[@fig:daybreak:solution-a]`. The archive labels a figure in `\obrazok`'s
    # own arguments, so by this point the mapping is known exactly and nothing has to be guessed.
    # A `\ref` to something else -- `\multiobrazok`, an `equation` -- has no target here and is
    # reported rather than turned into a link that resolves to nothing.
    def reference(m: re.Match) -> str:
        target = labels.get(m.group(1).strip())
        if target is None:
            notes.append(f'ref: `\\ref{{{m.group(1)}}}` points at a label this conversion did '
                         f'not create -- give it a `#fig:` or `#eq:` target by hand')
            return m.group(0)
        return f'[@fig:{target}]'

    text = re.sub(r'\\ref\{([^}]*)\}', reference, text)
    return text, wanted, notes


def find_figure(stem: str, ancient: Path, cache: Path) -> tuple[Path | None, list[str]]:
    """
    The SVG for a figure stem, exporting the `.odg` if that is all there is.

    The EPS beside these are *exports*; the `.svg` and `.odg` are the sources. 2009 has four
    figures with only the `.odg` -- `MAT/papier_ries`, `KIN/lietadlo_ries`, `KIN/kvapky_zad`
    and `KIN/kvapky_ries` -- and LibreOffice exports them with their text still text, which is
    what makes the font pass below work on them. The export goes to a cache under `--out`,
    never back into the archive, which is a read-only clone.
    """
    for svg in ancient.rglob(f'{stem}.svg'):
        return svg, []
    cached = cache / f'{stem}.svg'
    if cached.exists():
        return cached, []
    for odg in ancient.rglob(f'{stem}.odg'):
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(['soffice', '--headless', '--convert-to', 'svg',
                        '--outdir', str(cache), str(odg)],
                       check=True, capture_output=True, timeout=300)
        if not cached.exists():
            return None, []
        # Before the crop, because a label wrapped onto two lines makes the drawing taller than
        # it is and the crop would take its bounding box from that.
        unwrapped, notes = svgfix.unwrap(cached.read_text(encoding='utf-8'))
        cached.write_text(unwrapped, encoding='utf-8')
        # LibreOffice exports the whole page, so the drawing arrives on an A4 sheet with the
        # rest of it blank -- 1588x2246 against the 229x266 of the drawing itself. A `height=`
        # on such a figure would size the sheet and shrink the picture to nothing, so crop to
        # the drawing here rather than leaving a trap for whoever sets the height.
        subprocess.run(['inkscape', '--export-type=svg', '--export-area-drawing',
                        '--export-plain-svg', '-o', str(cached), str(cached)],
                       check=True, capture_output=True, timeout=300)
        return cached, notes
    # Last, and only last: an `.eps` is an *export*, and a `.odg` or `.svg` beside it is the
    # thing it was exported from. Preferring it would throw away the text of every figure that
    # still has its source -- which is what it did to volume 12's four ODG drawings.
    for eps in ancient.rglob(f'{stem}.eps'):
        cache.mkdir(parents=True, exist_ok=True)
        return _from_eps(eps, cache / f'{stem}.svg')
    return None, []


def _ink(svg: Path) -> float:
    """How much of a rendering is not white. Zero when nothing drew."""
    png = svg.with_suffix('.check.png')
    try:
        subprocess.run(['rsvg-convert', '-z', '1', '-b', 'white', '-o', str(png), str(svg)],
                       check=True, capture_output=True, timeout=120)
        out = subprocess.run(['magick', str(png), '-format', '%[fx:1-mean]', 'info:'],
                             check=True, capture_output=True, timeout=120, text=True)
        return float(out.stdout.strip() or 0)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return 0.0
    finally:
        png.unlink(missing_ok=True)


def _from_eps(eps: Path, out: Path) -> tuple[Path | None, list[str]]:
    r"""
    An EPS export -> SVG, keeping the text as text where that is possible at all.

    2012 is EPS-only for 15 of its 21 figures: no `.svg`, no `.odg`, and the `.eps` is a cairo
    or StarOffice export rather than a build product of anything we still have. Ghostscript
    turns it into a PDF, and then there are two ways on, neither of which always works:

    - **`mutool convert -F svg -O text=text`** keeps the text as real `<text>` with the font
      named, which is what the Minion pass needs. It relies on the embedded subset carrying a
      **ToUnicode** map, and `pdffonts` shows several of 2012's do not -- a cmmi12 without one
      comes out as a row of U+FFFD. It also silently dropped every hairline stroke of
      `OPT/sosovky`, which converted to a blank page.
    - **`pdftocairo -svg`** always draws what the PDF draws, and outlines every glyph into a
      path. Correct on the page, and unreachable by any font pass afterwards.

    So mutool is tried first and kept only if it produced no U+FFFD and drew about as much ink
    as pdftocairo did; otherwise the outlined version is used and the loss is reported.
    """
    pdf = out.with_suffix('.pdf')
    subprocess.run(['gs', '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER', '-sDEVICE=pdfwrite',
                    '-dEPSCrop', f'-sOutputFile={pdf}', str(eps)],
                   check=True, capture_output=True, timeout=300)

    outlined = out.with_suffix('.outlined.svg')
    subprocess.run(['pdftocairo', '-svg', str(pdf), str(outlined)],
                   check=True, capture_output=True, timeout=300)

    textual = out.with_suffix('.text.svg')
    subprocess.run(['mutool', 'convert', '-F', 'svg', '-O', 'text=text',
                    '-o', str(out.parent / f'{out.stem}%d.svg'), str(pdf)],
                   check=True, capture_output=True, timeout=300)
    pages = sorted(out.parent.glob(f'{out.stem}[0-9]*.svg'))
    for extra in pages[1:]:
        extra.unlink()
    note = []
    if pages:
        pages[0].replace(textual)
        body = textual.read_text(encoding='utf-8', errors='replace')
        # A numeric character reference is mutool saying it had no Unicode for that glyph
        # and is passing the raw byte through: `&#xdf;` where a `V` was meant. Those come
        # out as tofu on the page, so they count as a failed conversion exactly as U+FFFD
        # does -- and they are what `pdffonts`' `uni: no` column predicts.
        lost = ('\ufffd' in body
                or re.search(r'&#x?[0-9A-Fa-f]+;', body) is not None)
        if not lost and _ink(textual) >= 0.8 * _ink(outlined):
            textual.replace(out)
            outlined.unlink(missing_ok=True)
            pdf.unlink(missing_ok=True)
            return out, []
        note = [f'eps: `{eps.name}` converted with its glyphs outlined -- '
                + ('the embedded font carries no ToUnicode map, so the characters cannot be '
                   'recovered' if lost else 'the text-preserving conversion lost part of the '
                   'drawing')
                + '. The drawing is right and the font pass cannot reach it.']
        textual.unlink(missing_ok=True)
    outlined.replace(out)
    pdf.unlink(missing_ok=True)
    return out, note or [f'eps: `{eps.name}` converted with its glyphs outlined; the font pass '
                         f'cannot reach them']


def convert_body(text: str, dialect: Dialect, slug: str, label: bool = False,
                 source_stem: str = '') -> tuple[str, list[str], list[str]]:
    """One `\\zadanie`/`\\vzorak`/`\\comment` body, through the whole table."""
    notes = list(dict.fromkeys(rules.report_only(text)))
    text = rules.decimal_braces(text)
    text = rules.trhaciealt(text)
    text, wanted, fig_notes = figures(text, dialect, slug, source_stem)
    notes += fig_notes
    text = rules.upright_units(text)
    text, unit_notes = rules.quantities(text)
    notes += unit_notes
    text, exponent_notes = rules.exponents(text)
    notes += exponent_notes
    text, over_notes = rules.over_to_frac(text)
    notes += over_notes
    for pattern, replacement in rules.SHORTHAND + rules.LINTED:
        text = pattern.sub(replacement, text)
    text = rules.quotes(text)
    text = rules.footnotes(text)
    text = rules.markup(text)
    text = rules.ties(text)
    text = rules.operator_spaces(text)
    text = rules.decimals(text)
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
    p.add_argument('--slugs', type=Path,
                   help='source path -> slug. Without it every problem takes its Slovak stem, '
                        'transliterated, which is enough for --dry-run and never enough for the '
                        'tree: a slug has to be readable and unique across every volume.')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--only', help='one source path, e.g. TAZ/kornutok.tex')
    p.add_argument('--dry-run', action='store_true', help='write the report and nothing else')
    a = p.parse_args()

    dialect = Dialect.read(a.ancient, a.year)
    slugs = yaml.safe_load(a.slugs.read_text()) if a.slugs else {}
    if not a.slugs and not a.dry_run:
        raise SystemExit('--slugs is required unless --dry-run: provisional names must not reach '
                         'the tree, where renaming one means moving a directory and rewriting '
                         'every `#fig:` and `#eq:` label inside it.')
    sources = order(a.ancient)
    report = [f'# {a.year} -> volume {a.volume:02d}\n',
              f'{len(sources)} problems in `priklady.tex`.\n']
    total = 0

    for number, rel in enumerate(sources, 1):
        if a.only and rel != a.only:
            continue
        slug = slugs.get(rel) or provisional(rel)
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
            converted, w, n = convert_body(body, dialect, slug,
                                           label=(macro == 'vzorak'),
                                           source_stem=Path(rel).stem)
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
            source, fig_notes = find_figure(stem, a.ancient, a.out / '.odg')
            for note in fig_notes:
                report.append(f'- figure: `{name}.svg` -- {note}\n')
            if source is None:
                report.append(f'- figure: no `{stem}.svg` and no `{stem}.odg` anywhere under '
                              f'{a.ancient}\n')
                continue
            fixed, others, n, greek = svgfix.repair(source.read_text(encoding='utf-8'))
            (out / f'{name}.svg').write_text(fixed, encoding='utf-8')
            for note in greek:
                report.append(f'- figure: `{name}.svg` -- {note}\n')
            if others:
                report.append(f'- figure: `{name}.svg` keeps {", ".join(others)} -- '
                              f'not a CM font, left alone\n')

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'report.md').write_text(''.join(report), encoding='utf-8')
    print(f'{len([s for s in sources if not a.only or s == a.only])} problem(s); '
          f'{total} thing(s) to decide; report at {a.out / "report.md"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
