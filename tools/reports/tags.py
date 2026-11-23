"""
A static HTML overview of every `phys` problem and its tags, grouped by volume.

    uv run python -m tools.reports.tags [-o output/reports/phys-tags.html] [--scope phys]

**The pool is deliberately out.** `phys/pool` holds problems nobody has set yet: no running
order, no volume, no date. Everything in this report is arranged by the volume meta's
`problems:` list, which *is* the running order, so a pool has nothing to arrange it by.

No JavaScript, no external request: the CSS is inlined and the page is one file, so it can be
opened from disk or sent to somebody as it stands -- the same bargain `core/html/page.py` makes.

A tag's colour is a hash of its own name, which is what makes it stable: adding a tag to the
vocabulary cannot recolour the others, and the same tag is the same colour in every volume and
in the index. `hashlib`, not `hash()`, because the built-in is salted per process and the page
would come out differently on every run.
"""
import argparse
import collections
import hashlib
import html
import pathlib
import sys
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def hue(tag: str) -> int:
    """A stable hue in [0, 360) for one tag."""
    return int.from_bytes(hashlib.md5(tag.encode()).digest()[:2], 'big') % 360


def tone(tag: str) -> int:
    """
    A second axis, 0-2, so that two tags landing on one hue still look different.

    59 tags over 360 hues collide by the birthday argument whatever the hash is -- six of
    phys's do, `buoyancy` with `thermo-process` and two more pairs. Spreading them by *index*
    instead would fix it and cost the property the hash is here for: a tag's colour would
    then depend on which other tags exist, so adding one to the vocabulary would recolour
    the rest. A third byte of the same digest keeps the colour a function of the name alone
    and takes the collisions down to the ones that share a hue *and* a tone.

    It shifts saturation and lightness, not hue, so the contrast stays where it was measured.
    """
    return hashlib.md5(tag.encode()).digest()[2] % 3


def read(path: pathlib.Path):
    """A meta, or None where it is absent or will not parse -- both are reported, not raised."""
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return None


def collect(source: pathlib.Path, competition: str):
    """Every volume of one competition, in order, with its problems in the running order."""
    root = source / competition
    volumes, problems = [], {}
    for directory in sorted(p for p in root.iterdir()
                            if (p / 'problems').is_dir() and not p.name.startswith('.')):
        if directory.name == 'pool':
            continue
        meta = read(directory / 'meta.yaml') or {}
        listed = meta.get('problems') if isinstance(meta.get('problems'), list) else []
        on_disk = {p.name for p in (directory / 'problems').iterdir() if p.is_dir()}
        rows = []
        for position, pid in enumerate(listed, 1):
            unit = read(directory / 'problems' / pid / 'meta.yaml')
            rows.append({'n': position, 'id': pid, 'exists': pid in on_disk,
                         'meta': unit, 'tags': list((unit or {}).get('tags') or []),
                         'idea': list(((unit or {}).get('authors') or {}).get('idea') or [])})
        volumes.append({'id': directory.name, 'date': meta.get('date'), 'rows': rows,
                        'unlisted': sorted(on_disk - set(listed))})
        problems[directory.name] = rows
    return volumes


def findings(volumes, vocabulary):
    """What the report warns about, as (kind, volume, detail) -- empty when the corpus is clean."""
    out = []
    for volume in volumes:
        for row in volume['rows']:
            # A listed problem with no directory is reported once, as that -- it has no meta
            # either, and saying both about one name is two lines for one defect.
            if not row['exists']:
                out.append(('listed but no directory', volume['id'], row['id']))
                continue
            if row['meta'] is None:
                out.append(('no meta.yaml at all', volume['id'], row['id']))
            elif not row['tags']:
                out.append(('no tags', volume['id'], row['id']))
            for tag in row['tags']:
                if vocabulary and tag not in vocabulary:
                    out.append(('a tag outside the vocabulary', volume['id'],
                                f"{row['id']} — {tag}"))
        for pid in volume['unlisted']:
            out.append(('a directory the running order does not name', volume['id'], pid))
    return out


def chip(tag: str, count: int | None = None) -> str:
    suffix = f'<span class="n">{count}</span>' if count is not None else ''
    return (f'<span class="tag t{tone(tag)}" style="--h:{hue(tag)}">'
            f'{html.escape(tag)}{suffix}</span>')


def render(volumes, warnings, counts, competition: str) -> str:
    total = sum(len(v['rows']) for v in volumes)
    credited = sum(1 for v in volumes for r in v['rows'] if r['idea'])
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    if warnings:
        grouped = collections.defaultdict(list)
        for kind, volume, detail in warnings:
            grouped[kind].append(f'{volume}/{detail}')
        body = ''.join(
            f'<p><strong>{html.escape(kind)}</strong> — {len(items)}</p><ul>'
            + ''.join(f'<li><code>{html.escape(i)}</code></li>' for i in items) + '</ul>'
            for kind, items in sorted(grouped.items()))
        banner = f'<section class="warn"><h2>{len(warnings)} to look at</h2>{body}</section>'
    else:
        banner = ('<section class="ok"><h2>Nothing to look at</h2><p>Every problem in every '
                  'volume carries at least one tag, every tag is in the vocabulary, and every '
                  'volume’s running order matches the directories beside it.</p></section>')

    index = ''.join(chip(t, n) for t, n in counts.most_common())

    sections = []
    for volume in volumes:
        date = volume['date'].strftime('%-d %B %Y') if hasattr(volume['date'], 'strftime') else ''
        rows = ''.join(
            f'<tr{"" if row["tags"] else " class=\"untagged\""}>'
            f'<td class="n">{row["n"]}</td>'
            f'<td class="pid"><code>{html.escape(row["id"])}</code></td>'
            f'<td class="idea">'
            + (html.escape(', '.join(row['idea'])) if row['idea']
               else '<span class="unknown">&mdash;</span>')
            + '</td>'
            '<td class="tags">'
            + (''.join(chip(t) for t in row['tags'])
               or '<span class="none">no tags</span>')
            + '</td></tr>'
            for row in volume['rows'])
        sections.append(
            f'<section class="volume"><h2 id="v{volume["id"]}">'
            f'<span class="vol">{html.escape(volume["id"])}</span>'
            f'<span class="meta">{html.escape(date)} · {len(volume["rows"])} problems</span></h2>'
            f'<table><thead><tr><th class="n">#</th><th>problem</th><th>idea</th>'f'<th>tags</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></section>')

    nav = ''.join(f'<a href="#v{v["id"]}">{html.escape(v["id"])}</a>' for v in volumes)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Náboj {html.escape(competition)} — tags</title>
<style>
:root {{
  --ink: #16181d; --dim: #6b7280; --line: #e3e5ea; --bg: #ffffff; --panel: #f7f8fa;
  --warn-bg: #fff6ed; --warn-line: #f0b27a; --warn-ink: #8a4b08;
  --ok-bg: #f0f8f2; --ok-line: #9fd0ab; --ok-ink: #1f6b33;
  --chip-bg: hsl(var(--h) 68% 92%); --chip-ink: hsl(var(--h) 60% 26%);
  --chip-line: hsl(var(--h) 45% 80%);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ink: #e7e9ee; --dim: #9aa1ad; --line: #2b2f37; --bg: #14161a; --panel: #1b1e24;
    --warn-bg: #2d1f10; --warn-line: #7a4f1d; --warn-ink: #f0b27a;
    --ok-bg: #132117; --ok-line: #2f5c3a; --ok-ink: #9fd0ab;
    --chip-bg: hsl(var(--h) 40% 20%); --chip-ink: hsl(var(--h) 70% 78%);
    --chip-line: hsl(var(--h) 35% 32%);
  }}
}}
:root[data-theme="dark"] {{
  --ink: #e7e9ee; --dim: #9aa1ad; --line: #2b2f37; --bg: #14161a; --panel: #1b1e24;
  --warn-bg: #2d1f10; --warn-line: #7a4f1d; --warn-ink: #f0b27a;
  --ok-bg: #132117; --ok-line: #2f5c3a; --ok-ink: #9fd0ab;
  --chip-bg: hsl(var(--h) 40% 20%); --chip-ink: hsl(var(--h) 70% 78%);
  --chip-line: hsl(var(--h) 35% 32%);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 2.5rem 16px 5rem; }}
h1 {{ font-size: 1.6rem; margin: 0 0 .25rem; letter-spacing: -.01em; }}
.sub {{ color: var(--dim); margin: 0 0 2rem; font-size: .9rem; }}
.counts {{ display: flex; flex-wrap: wrap; gap: .5rem 2rem; margin: 0 0 2rem;
  padding: 1rem 1.2rem; background: var(--panel); border: 1px solid var(--line);
  border-radius: 10px; }}
.counts div {{ min-width: 7rem; }}
.counts b {{ display: block; font-size: 1.5rem; font-weight: 650; line-height: 1.2; }}
.counts span {{ color: var(--dim); font-size: .8rem; }}
.warn, .ok {{ border-radius: 10px; padding: 1rem 1.2rem; margin: 0 0 2rem; }}
.warn {{ background: var(--warn-bg); border: 1px solid var(--warn-line); color: var(--warn-ink); }}
.ok {{ background: var(--ok-bg); border: 1px solid var(--ok-line); color: var(--ok-ink); }}
.warn h2, .ok h2 {{ font-size: 1rem; margin: 0 0 .5rem; }}
.warn ul {{ margin: .25rem 0 1rem; padding-left: 1.2rem; }}
.warn p {{ margin: .5rem 0 0; }}
h2 {{ font-size: 1.1rem; margin: 2.5rem 0 .75rem; display: flex; align-items: baseline;
  gap: .75rem; border-bottom: 1px solid var(--line); padding-bottom: .4rem; }}
h2 .vol {{ font-variant-numeric: tabular-nums; font-size: 1.3rem; font-weight: 650; }}
h2 .meta {{ color: var(--dim); font-size: .85rem; font-weight: 400; }}
nav {{ display: flex; flex-wrap: wrap; gap: .3rem; margin: 0 0 2rem; }}
nav a {{ display: inline-block; padding: .2rem .55rem; border: 1px solid var(--line);
  border-radius: 6px; color: var(--ink); text-decoration: none;
  font-variant-numeric: tabular-nums; font-size: .85rem; }}
nav a:hover {{ background: var(--panel); }}
.index {{ display: flex; flex-wrap: wrap; gap: .35rem; margin: 0 0 1rem; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ text-align: left; font-size: .75rem; text-transform: uppercase; letter-spacing: .06em;
  color: var(--dim); font-weight: 600; padding: .35rem .5rem; }}
td {{ padding: .4rem .5rem; border-top: 1px solid var(--line); vertical-align: top; }}
tbody tr:hover {{ background: var(--panel); }}
td.n, th.n {{ width: 2.5rem; text-align: right; color: var(--dim);
  font-variant-numeric: tabular-nums; }}
td.pid {{ width: 15rem; }}
td code, .warn code {{ font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; }}
td.idea {{ width: 11rem; color: var(--ink); font-size: .85rem; }}
/* 247 of 1109 problems record an idea author, so most of this column is blank. The marker is
   muted on purpose -- a loud one would read as 878 defects rather than as unrecorded, which is
   what `authors-empty` in `core/audit` is for and what an archive honestly looks like. */
td.idea .unknown {{ color: var(--line); }}
tr.untagged {{ background: var(--warn-bg); }}
.none {{ color: var(--warn-ink); font-size: .8rem; font-style: italic; }}
.tag {{ display: inline-block; margin: 1px 2px 1px 0; padding: .1rem .45rem;
  background: var(--chip-bg); color: var(--chip-ink); border: 1px solid var(--chip-line);
  border-radius: 5px; font-size: .78rem; font-weight: 550; white-space: nowrap; }}
.tag .n {{ margin-left: .35rem; opacity: .65; font-weight: 400;
  font-variant-numeric: tabular-nums; }}
/* The second axis: two tags on one hue differ unless they share a tone as well. */
.tag.t1 {{ --chip-bg: hsl(var(--h) 46% 88%); --chip-line: hsl(var(--h) 34% 74%); }}
.tag.t2 {{ --chip-bg: hsl(var(--h) 88% 94%); --chip-line: hsl(var(--h) 60% 83%); }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) .tag.t1 {{ --chip-bg: hsl(var(--h) 24% 24%);
    --chip-line: hsl(var(--h) 22% 36%); }}
  :root:not([data-theme="light"]) .tag.t2 {{ --chip-bg: hsl(var(--h) 58% 17%);
    --chip-line: hsl(var(--h) 48% 29%); }}
}}
:root[data-theme="dark"] .tag.t1 {{ --chip-bg: hsl(var(--h) 24% 24%);
  --chip-line: hsl(var(--h) 22% 36%); }}
:root[data-theme="dark"] .tag.t2 {{ --chip-bg: hsl(var(--h) 58% 17%);
  --chip-line: hsl(var(--h) 48% 29%); }}
@media (max-width: 640px) {{
  td.pid, td.idea {{ width: auto; }}
  .counts {{ gap: .75rem 1.25rem; }}
}}
</style>
</head>
<body>
<div class="wrap">
<h1>Náboj {html.escape(competition)} — problems and tags</h1>
<p class="sub">{len(volumes)} volumes, the pool excluded · generated {stamp}</p>

<div class="counts">
  <div><b>{len(volumes)}</b><span>volumes</span></div>
  <div><b>{total}</b><span>problems</span></div>
  <div><b>{credited}</b><span>idea recorded</span></div>
  <div><b>{len(counts)}</b><span>distinct tags</span></div>
  <div><b>{sum(counts.values())}</b><span>tag assignments</span></div>
  <div><b>{sum(counts.values()) / total:.1f}</b><span>tags per problem</span></div>
</div>

{banner}

<h2><span class="vol">Tags</span><span class="meta">by how often they are used</span></h2>
<div class="index">{index}</div>

<h2><span class="vol">Volumes</span></h2>
<nav>{nav}</nav>

{''.join(sections)}
</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--competition', default='phys')
    parser.add_argument('--source', type=pathlib.Path, default=ROOT / 'source/naboj')
    parser.add_argument('-o', '--output', type=pathlib.Path,
                        default=ROOT / 'output/reports/phys-tags.html')
    args = parser.parse_args()

    try:
        from modules.naboj.builder.renderer import VALID_TAGS as vocabulary
    except ImportError:                                 # a checkout without the module on the path
        vocabulary = None

    volumes = collect(args.source, args.competition)
    if not volumes:
        print(f'{args.source / args.competition}: no volumes with a `problems/` directory',
              file=sys.stderr)
        return 1
    counts = collections.Counter(t for v in volumes for r in v['rows'] for t in r['tags'])
    warnings = findings(volumes, vocabulary)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(volumes, warnings, counts, args.competition))
    total = sum(len(v['rows']) for v in volumes)
    print(f'{args.output}: {len(volumes)} volumes, {total} problems, {len(counts)} tags, '
          f'{len(warnings)} warning(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
