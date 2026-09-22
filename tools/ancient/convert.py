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
import collections
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import yaml

from tools.ancient import figures as svgfix
from tools.ancient import rules
from tools.ancient.dialect import Dialect
from tools.ancient.lex import calls, macro_body, match_brace, strip_comments


def order(ancient: Path, monolith: str | None = None,
          encoding: str = 'utf-8') -> list[str]:
    r"""
    The running order, as keys that `read_problem` can resolve.

    Two shapes, because 2007 predates the one every year after it uses. From 2009 on there is a
    `priklady.tex` holding nothing but `\priklad{DIR/slug.tex}` lines, and a line's position in
    it was the problem's printed number, so the key is the path. 2007 has no such list: its
    `07priklady.tex` *is* the problems, one `\zadanie`/`\vzorak`/`\comment` group after another,
    and the number is simply the position of the group. The key is then `<file>#<n>`.
    """
    if monolith:
        text = _text(ancient / monolith, encoding)
        return [f'{monolith}#{i}'
                for i, _ in enumerate(re.finditer(r'(?m)^\\zadanie(?![a-zA-Z])', text), 1)]
    text = _text(ancient / 'priklady.tex', encoding)
    return [m.group(1).strip()
            for m in re.finditer(r'^[^%\n]*\\priklad\{\s*(.*?)\s*\}', text, re.MULTILINE)]


def _text(path: Path, encoding: str) -> str:
    """One archive file, decoded and with its line endings normalised."""
    text = path.read_text(encoding=encoding, errors='replace')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def read_problem(ancient: Path, rel: str, encoding: str = 'utf-8') -> str | None:
    r"""
    One problem's TeX, or None if the archive has not got it.

    A `<file>#<n>` key names the nth `\zadanie` group of a monolith and everything up to the
    next one, which is exactly the statement, the solution and the answer. A `\extra` group --
    2007 has six, a bonus sheet that was never part of the round -- is not a `\zadanie` and so
    is never a block: the `31 problems` the organisers' own report names are the 31 this finds.
    """
    if '#' in rel:
        name, index = rel.rsplit('#', 1)
        path = ancient / name
        if not path.is_file():
            return None
        text = _text(path, encoding)
        starts = [m.start() for m in re.finditer(r'(?m)^\\zadanie(?![a-zA-Z])', text)]
        i = int(index) - 1
        if not 0 <= i < len(starts):
            return None
        rest = re.search(r'(?m)^\\(?:zadanie|extra)(?![a-zA-Z])', text[starts[i] + 1:])
        end = starts[i] + 1 + rest.start() if rest else len(text)
        return text[starts[i]:end]
    path = ancient / rel
    return _text(path, encoding) if path.is_file() else None


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


def figures(text: str, dialect: Dialect, slug: str, body_role: str = 'problem',
            seen: dict[str, str] | None = None) -> tuple[str, list[str], list[str]]:
    r"""
    `\obrazok`/`\pict`/`\includegraphics` -> `![](x.svg){#fig:slug height=…}`.

    Returns the rewritten text, the figure stems wanted, and notes. The height is always
    reported: it is a visual choice and the old `scale` does not carry over.
    """
    notes, wanted = [], []
    #: Archive stem -> the name it was given, shared across one problem's three bodies. An
    #: answer that shows the solution's picture names the *same* drawing, and converting the
    #: bodies one at a time would otherwise give it a second name and a second copy of the
    #: file -- which is what four of 2013's problems, and three of volumes 12, 13 and 15's,
    #: had to have undone by hand.
    seen = {} if seen is None else seen
    #: How many figures of each role this body has so far, so they can be numbered -- and,
    #: at the end, so that a role with exactly one can drop its number again.
    counts: collections.Counter[str] = collections.Counter()
    #: The year's own `\label{}` -> the `#fig:` label it became, so `\ref{}` can be rewritten.
    labels: dict[str, str] = {}

    def markdown(path: str, caption: str = '', tag: str = '') -> str:
        stem = Path(path.strip()).stem
        # A figure is named after the *role* it plays, not after its problem: the directory
        # already says which problem this is, and `crane/lift.svg`, `northern-sun/solstices.svg`
        # are what the finished volumes look like. So `problem.svg` and `solution.svg`, matching
        # `problem.md` and `solution.md` beside them.
        #
        # The role comes from the archive's own suffix where there is one -- `_zad` is the
        # statement's and `_ries` the solution's, each optionally numbered or lettered when a
        # problem has several (`korytko_ries1`, `den_ries_A`) -- and otherwise simply from the
        # body being converted, which knows. Guessing it from the filename instead put 2012's
        # `DYN/kopce.eps`, which is referenced in a solution, into `problem.svg`.
        part = re.match(r'^(?P<body>.*?)[-_](?:o[-_])?(?P<which>zad|ries)[-_]?'
                        r'(?P<index>[0-9A-Za-z]*)$', stem)
        if stem in seen:
            name = seen[stem]
        else:
            role = ('problem' if part['which'] == 'zad' else 'solution') if part else body_role
            counts[role] += 1
            name = seen[stem] = f'{role}-{counts[role]}'
            wanted.append((stem, name))
        if tag:
            labels[tag.strip()] = f'{slug}:{name}'
        notes.append(f'figure: `{name}.svg` -- set a real height, 40mm is a placeholder')
        # `#fig:<id>` or `#fig:<id>:<name>`, and nothing else: `markdown-check`'s `lfn` rule
        # rejects a label that does not open with the problem's own id -- and rejects a label
        # in an `answer.md` outright, whatever it says, since only a statement and a solution
        # may carry one. An answer's picture is therefore written bare.
        label = '' if body_role == 'answer' else f'#fig:{slug}:{name} '
        return f'![{caption.strip()}]({name}.svg){{{label}height=40mm}}'

    # One pass in document order, not one pass per macro. A solution may draw with `\pict` in
    # one place and `\includegraphics` in another -- 2010's `DYN/skatula` does exactly that --
    # and taking every `\pict` before any `\includegraphics` numbered its two figures the
    # wrong way round, so `solution-1` was the picture that came second on the page.
    def earliest():
        best = None
        # Every macro the year's own `include.tex` defines as drawing a figure, not just
        # `\obrazok`: 2014 also has `\zadobrazok` and `\obtekobrazok`, and a problem whose only
        # picture was one of those converted without it and said nothing.
        for name, (arity, file, caption, label) in dialect.figures.items():
            for start, end, args in calls(text, name, arity):
                cap = args[caption] if caption is not None else ''
                tag = args[label] if label is not None else ''
                if best is None or start < best[0]:
                    best = (start, end, args[file], cap, tag)
                break                       # `calls` yields in order; the rest are later
        m = re.search(r'\\includegraphics(?:\[[^\]]*\])?\s*(?=\{)', text)
        if m and (best is None or m.start() < best[0]):
            e = match_brace(text, m.end())
            best = (m.start(), e, text[m.end() + 1:e - 1], '', '')
        return best

    while (found := earliest()) is not None:
        start, end, path, cap, tag = found
        # A figure stands on its own line. 2014 wraps one in a `wrapfigure` in the middle of a
        # paragraph -- `DYN/rebrina` -- and the prose ran on straight after the attribute block,
        # which Markdown reads as part of the caption's line and the lint as one long line.
        head = '' if start == 0 or text[start - 1] == '\n' else '\n'
        tail = '' if end >= len(text) or text[end] == '\n' else '\n'
        text = text[:start] + head + markdown(path, cap, tag) + tail + text[end:]

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

    # A role with one figure needs no number, and the statement's only figure takes the bare
    # `#fig:<id>` the `lfn` rule expects of a problem.
    for role, count in counts.items():
        if count != 1:
            continue
        text = text.replace(f']({role}-1.svg)', f']({role}.svg)')
        text = text.replace(f'{{#fig:{slug}:{role}-1 ', f'{{#fig:{slug} ' if role == 'problem'
                            else f'{{#fig:{slug}:{role} ')
        # The `\ref{}`s were rewritten before this, off the names as they then stood, so the
        # cross-references have to come along -- five of 2014's pointed at a `solution-1` that
        # had since become `solution`, and the audit called every one of them dangling.
        text = text.replace(f'[@fig:{slug}:{role}-1]',
                            f'[@fig:{slug}]' if role == 'problem' else f'[@fig:{slug}:{role}]')
        wanted[:] = [(s, role if n == f'{role}-1' else n) for s, n in wanted]
        for stem, given in seen.items():
            if given == f'{role}-1':
                seen[stem] = role
        for tag, target in labels.items():
            if target == f'{slug}:{role}-1':
                labels[tag] = slug if role == 'problem' else f'{slug}:{role}'
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
    cached = cache / f'{stem}.svg'
    for svg in ancient.rglob(f'{stem}.svg'):
        if _fills_its_canvas(svg):
            return svg, []
        # 2013 drew every figure on a full A4 sheet and left it there -- `ELEK/boromir.svg` is
        # 614x587 of drawing on 745x1053 of page. That is the same trap the `.odg` export below
        # is cropped for: a `height=` would size the *sheet*, so the drawing comes out at half
        # the height asked for, with the rest of the box empty. Crop into the cache, never over
        # the archive, which is a read-only clone.
        cache.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(svg, cached)
        _crop(cached)
        return cached, [f'figure: `{stem}` was drawn on a whole page and has been cropped '
                        f'to the drawing']
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
        _crop(cached)
        return cached, notes
    # Last, and only last: an `.eps` is an *export*, and a `.odg` or `.svg` beside it is the
    # thing it was exported from. Preferring it would throw away the text of every figure that
    # still has its source -- which is what it did to volume 12's four ODG drawings.
    for eps in ancient.rglob(f'{stem}.eps'):
        cache.mkdir(parents=True, exist_ok=True)
        return _from_eps(eps, cache / f'{stem}.svg')
    return None, []


def _crop(svg: Path) -> None:
    """Shrink the canvas to the drawing, in place."""
    subprocess.run(['inkscape', '--export-type=svg', '--export-area-drawing',
                    '--export-plain-svg', '-o', str(svg), str(svg)],
                   check=True, capture_output=True, timeout=300)


def _fills_its_canvas(svg: Path, enough: float = 0.75) -> bool:
    """
    Is this drawing already the size of its own canvas, or is it adrift on a page?

    Measured off a rendering rather than off the geometry, because the geometry is whatever
    the drawing program left behind -- `width` in one unit, a `viewBox` in another, groups
    with transforms on them. The two populations do not overlap and the threshold sits in the
    gap between them: the tightest figure in volumes 12, 13 and 15 covers 0.87 of its canvas
    (`12/galvanometer`, which has a little slack under it and is left alone), and the loosest
    of 2013's whole-page drawings covers 0.65. Anything that fails to render measures zero and
    is cropped, which is the harmless way round.
    """
    png = svg.with_suffix('.canvas.png')
    try:
        subprocess.run(['rsvg-convert', '-z', '1', '-b', 'white', '-o', str(png), str(svg)],
                       check=True, capture_output=True, timeout=120)
        def measure(*trim):
            out = subprocess.run(['magick', str(png), *trim, '-format', '%w %h', 'info:'],
                                 check=True, capture_output=True, timeout=120, text=True)
            return (float(x) for x in out.stdout.split())

        w, h = measure()
        tw, th = measure('-trim')
        return tw >= enough * w and th >= enough * h
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return False
    finally:
        png.unlink(missing_ok=True)


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
                 role: str = 'problem',
                 seen: dict[str, str] | None = None) -> tuple[str, list[str], list[str]]:
    """One `\\zadanie`/`\\vzorak`/`\\comment` body, through the whole table."""
    # The archive indents a macro's body as TeX source -- 2015 writes every `\vzorak{%` with
    # its prose four spaces in, and 50 of its files are like that. TeX does not care; Markdown
    # reads four spaces as a code block, so the whole solution came out verbatim and ran off
    # the page. Dedent before anything else; the displays and lists below add their own indent.
    # Tabs first: 2015's English mixes three spaces, four spaces and a tab, and `dedent` takes
    # the *common* prefix, which a single tab line reduces to nothing at all.
    text = textwrap.dedent(text.expandtabs(4))
    notes = list(dict.fromkeys(rules.report_only(text)))
    # The year's own shorthands, before anything reads what they stand for.
    for name, body in dialect.shorthands().items():
        text = re.sub(rf'\\{name}(?![a-zA-Z])', body.replace('\\', '\\\\'), text)
    text = rules.layout(text)
    text, list_notes = rules.lists(text)
    notes += list_notes
    text = rules.thin_comma(text)
    text = rules.decimal_braces(text)
    text = rules.trhaciealt(text)
    text, wanted, fig_notes = figures(text, dialect, slug, role, seen)
    notes += fig_notes
    text = rules.spaced_units(text)
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
    # Whatever `\,` is left is optical spacing -- before a `\frac`, a differential or a unit
    # letter. `decimals` has already turned the ones that grouped digits into `\num{}`, the
    # `tgc` rule bans the rest, and volumes 12, 13, 15 and 16 have none between them.
    text = re.sub(r'\\,(?=\s*[\\a-zA-Z])', '', text)
    text = rules.fractions(text, role)
    text = rules.lone_dollars(text)
    text, display_notes = rules.displays(text, slug if label else None)
    notes += display_notes
    text = rules.inline_math(text)
    text = rules.line_breaks(text)
    text = rules.break_displays(text)
    text = rules.wrap(text)
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
    p.add_argument('--language', default='sk',
                   help="the language of this `--ancient` tree. `answer.md` is shared across "
                        "languages and is written whichever is converted, so a second language "
                        "overwrites the first's -- convert the one whose answers you want last, "
                        "or keep the answer from the first and let the rest be a comparison.")
    p.add_argument('--monolith',
                   help='the archive file that IS the problems, one `\\zadanie` group\n'
                        'after another, when the year has no `priklady.tex` list of\n'
                        '`\\priklad{}` includes. 2007 is the only such year.')
    p.add_argument('--encoding', default='utf-8',
                   help="the archive's own encoding; 2007 is `iso-8859-2`.")
    p.add_argument('--only', help='one source path, e.g. TAZ/kornutok.tex')
    p.add_argument('--dry-run', action='store_true', help='write the report and nothing else')
    a = p.parse_args()

    dialect = Dialect.read(a.ancient, a.year)
    slugs = yaml.safe_load(a.slugs.read_text()) if a.slugs else {}
    if not a.slugs and not a.dry_run:
        raise SystemExit('--slugs is required unless --dry-run: provisional names must not reach '
                         'the tree, where renaming one means moving a directory and rewriting '
                         'every `#fig:` and `#eq:` label inside it.')
    sources = order(a.ancient, a.monolith, a.encoding)
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
        body = read_problem(a.ancient, rel, a.encoding)
        if body is None:
            # 2011 lists six problems whose `.tex` is not in the archive; the round ran, so the
            # entry stays in `problems:` and the booklet prints `\protectedInput`'s red
            # `Missing file` box. A hole in a past round is a fact, and should be loud.
            report.append(f'\n## {number}. `{rel}` -> `{slug}`\n')
            report.append(f'- **source lost** -- no `{rel}` under {a.ancient}; list the slug in '
                          f'the volume meta and let the booklet say so\n')
            total += 1
            continue
        raw = strip_comments(body)
        out = a.out / 'problems' / slug
        notes, wanted = [], []
        #: One map per problem, so the three bodies agree on what each drawing is called.
        seen: dict[str, str] = {}
        pieces = {}
        for macro, target in ((('zadanie', f'{a.language}/problem.md'),
                               ('vzorak', f'{a.language}/solution.md'),
                               ('comment', 'answer.md'))):
            body = macro_body(raw, macro)
            if body is None:
                notes.append(f'{macro}: absent from the source')
                continue
            converted, w, n = convert_body(body, dialect, slug,
                                           label=(macro == 'vzorak'),
                                           role={'zadanie': 'problem',
                                                 'vzorak': 'solution'}.get(macro, 'answer'),
                                           seen=seen)
            pieces[target] = (converted, list(n))
            wanted += w
            notes += [f'{macro}: {x}' for x in n]

        solution, answer = pieces.get(f'{a.language}/solution.md'), pieces.get('answer.md')
        if solution and answer and solution[0] == answer[0]:
            note = 'identical to the comment -- this problem has no model solution'
            notes.append(f'vzorak: {note}')
            pieces[f'{a.language}/solution.md'][1].append(note)
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
