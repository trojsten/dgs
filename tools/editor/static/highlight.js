// Minimal dependency-free syntax highlighter for the DGS Markdown+Jinja DSL, meta.yaml and the
// TeX pandoc produces. No external library — just a priority-ordered, non-overlapping regex
// tokenizer.
//
// It does one thing beyond colouring: a span that names something an author can look up carries
// `data-ref="<kind>:<name>"`, keyed exactly as `/api/reference` keys its entries, so the hover in
// `app.js` does one dictionary lookup and no parsing. See `collectReferences`.

const RULES = {
  "dgs-md": [
    { re: /\(§[\s\S]*?§\)/g, cls: "tok-jinja" },
    { re: /\$\$[\s\S]*?\$\$/g, cls: "tok-math" },
    { re: /\$[^$\n]+?\$/g, cls: "tok-math" },
    { re: /\{#[^}\n]*\}/g, cls: "tok-label" },
    { re: /^#{1,6}\s.*$/gm, cls: "tok-heading" },
    { re: /\\[A-Za-z]+/g, cls: "tok-cmd" },
    { re: /\*\*[^*\n]+?\*\*/g, cls: "tok-em" },
  ],
  // Gnuplot scripts and their data tables. The `(§ … §)` tags are the whole reason a .gp is
  // edited here rather than in an editor that knows gnuplot: they are what ties the graph to
  // meta.yaml. Comments and strings are along for the ride; the rest is left alone.
  "dgs-gnuplot": [
    { re: /\(§[\s\S]*?§\)/g, cls: "tok-jinja" },
    { re: /#.*/g, cls: "tok-comment" },
    { re: /'[^'\n]*'|"[^"\n]*"/g, cls: "tok-string" },
    { re: /(?<![\w.])-?\d+(\.\d+)?\b/g, cls: "tok-number" },
  ],
  // The TeX pandoc produces, which is what the TeX tab shows. Note it emits `\(…\)` and
  // `\[…\]` rather than `$…$`, so those come first; `$…$` is here for hand-written TeX.
  //
  // Commands outrank maths deliberately, the opposite way round from `dgs-md`. Generated TeX is
  // mostly `\qty{…}{…}` *inside* maths, and a maths span that swallowed every command in it
  // would be one flat colour -- so the commands are claimed first and the delimiters keep what
  // is left.
  "dgs-tex": [
    { re: /(?<!\\)%.*/g, cls: "tok-comment" },
    { re: /\\(?:begin|end)\{[^}\n]*\}/g, cls: "tok-heading" },
    { re: /\\[A-Za-z@]+\*?/g, cls: "tok-cmd" },
    { re: /\\[(\[][\s\S]*?\\[)\]]/g, cls: "tok-math" },
    { re: /\$\$[\s\S]*?\$\$|\$[^$\n]+?\$/g, cls: "tok-math" },
    { re: /(?<![\w.])-?\d+(\.\d+)?\b/g, cls: "tok-number" },
  ],
  "dgs-yaml": [
    { re: /#.*/g, cls: "tok-comment" },
    { re: /'[^'\n]*'|"[^"\n]*"/g, cls: "tok-string" },
    { re: /^\s*-\s*[\w-]+(?=:)/gm, cls: "tok-key" },
    { re: /^\s*[\w-]+(?=:)/gm, cls: "tok-key" },
    { re: /(?<![\w.])-?\d+(\.\d+)?\b/g, cls: "tok-number" },
  ],
};

// The five names that are namespaces rather than quantities. `eq.kin` is an `eq:` entry and
// `const.g` is a constant — neither is an attribute of anything, so the attribute rule must not
// claim what follows the dot. The first three are `meta.yaml` keys and have entries under that
// kind; `const` and `i18n` are added by the context and have their own.
const NAMESPACES = { eq: "meta-key", words: "meta-key", blocks: "meta-key",
                     const: "namespace", i18n: "namespace" };

// Names *inside* a Jinja tag, which the tag rule would otherwise swallow whole. Run at a higher
// priority than the tag itself, so the existing carving splits the tag into flat siblings around
// them — no nesting, which keeps `highlight`'s output shape and the tests that read it.
//
// Order is the priority, and it settles two real collisions: `|snap(0.5)` is a filter and not a
// call, and `d.to('m')` is an attribute and not a global. Whichever claims the name first wins,
// and the later rule's overlapping range is carved away to nothing.
const INNER = [
  { re: /\|\s*([A-Za-z_]\w*)/g, cls: "tok-jinja-filter", kind: "filter" },
  { re: /\b([A-Za-z_]\w*)(?=\.)/g, cls: "tok-jinja-ns", namespace: true },
  { re: /\.([A-Za-z_]\w*)/g, cls: "tok-jinja-attr", kind: "attribute", notAfterNamespace: true },
  { re: /([A-Za-z_]\w*)\s*\(/g, cls: "tok-jinja-call", kind: "global" },
  // The range operator, which is how every answer interval in the sources is written — `QR` is
  // never spelled out. Spaces on both sides are required so that the `%` of a `'%02d'` format
  // string is not claimed as one.
  { re: /(?<=\s)%(?=\s)/g, cls: "tok-jinja-op", kind: "operator", whole: true },
];

// Where `INNER` applies. In Markdown and gnuplot that is inside a `(§ … §)`; in a meta it is the
// values of `derived:`, which is where `PQ`, `QL` and `.to()` are actually written — 158 of the
// 160 `PQ` in the repository are there and two are in a tag.
const TAG = /\(§[\s\S]*?§\)/g;

function tagRegions(text) {
  const regions = [];
  const re = new RegExp(TAG.source, TAG.flags);
  let m;
  while ((m = re.exec(text))) regions.push([m.index, m.index + m[0].length]);
  return regions;
}

// A meta is line-structured, so the block a line belongs to is a scan rather than a parse: a
// top-level key at column 0 opens a block and the indented lines under it belong to that block.
// Cheaper and more honest than a YAML parser for a buffer that is edited character by character
// and is therefore invalid half the time.
function yamlBlocks(text) {
  const blocks = [];
  let offset = 0;
  let current = null;
  for (const line of text.split("\n")) {
    const top = /^([\w-]+):/.exec(line);
    if (top) current = top[1];
    else if (line.trim() && !/^\s/.test(line)) current = null;
    blocks.push({ key: current, start: offset, end: offset + line.length, line });
    offset += line.length + 1;
  }
  return blocks;
}

// Where a YAML comment starts on a line, or the line's length if it has none. A `#` inside a
// quoted scalar is not one, and YAML requires whitespace before an inline `#`, so both tests are
// cheap. Needed because a comment in a `derived:` block is prose *about* the expression — one
// saying "note the .to() there" would otherwise offer a tooltip on its own prose.
function commentStart(line) {
  let quote = null;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quote) { if (ch === quote) quote = null; continue; }
    if (ch === "'" || ch === '"') { quote = ch; continue; }
    if (ch === "#" && (i === 0 || /\s/.test(line[i - 1]))) return i;
  }
  return line.length;
}

function collectReferences(text, lang) {
  const found = [];
  const push = (start, end, cls, ref) => found.push({ start, end, cls, ref, priority: -1 });

  let regions = [];
  if (lang === "dgs-md" || lang === "dgs-gnuplot") {
    regions = tagRegions(text);
  } else if (lang === "dgs-yaml") {
    const blocks = yamlBlocks(text);
    // `derived:` holds Jinja expressions; a tag may also appear in an `eq:` or a `blocks:` entry.
    for (const block of blocks) {
      if (block.key !== "derived" || !/^\s/.test(block.line)) continue;
      const cut = commentStart(block.line);
      if (cut > 0) regions.push([block.start, block.start + cut]);
    }
    regions = regions.concat(tagRegions(text));
    // A key is a name an author can look up too: `derived:` at column 0, and `magnitude:` and its
    // seven siblings inside `values:`. A key that is neither — a quantity's own name — emits a ref
    // that the table simply does not hold, and a miss shows nothing, which is the right outcome.
    //
    // Inside `values:` there are two levels and they mean different things: the shallower keys
    // are the quantities' own names, which the table cannot hold and should not claim to, and the
    // deeper ones are `magnitude:` and its seven siblings. The name level is whichever indent
    // comes first, rather than a hard-coded two spaces, so a meta indented otherwise still works.
    let nameLevel = null;
    for (const block of blocks) {
      if (block.key !== "values") continue;
      const key = /^(\s+)[\w-]+(?=:)/.exec(block.line);
      if (key && (nameLevel === null || key[1].length < nameLevel)) nameLevel = key[1].length;
    }
    for (const block of blocks) {
      const key = /^(\s*)([\w-]+)(?=:)/.exec(block.line);
      if (!key) continue;
      const at = block.start + key[1].length;
      if (!key[1].length) push(at, at + key[2].length, "tok-key", `meta-key:${key[2]}`);
      else if (block.key === "values" && nameLevel !== null && key[1].length > nameLevel)
        push(at, at + key[2].length, "tok-key", `values-key:${key[2]}`);
    }
  }

  for (const [from, to] of regions) {
    const slice = text.slice(from, to);
    for (const rule of INNER) {
      const re = new RegExp(rule.re.source, rule.re.flags);
      let m;
      while ((m = re.exec(slice))) {
        if (m[0].length === 0) { re.lastIndex++; continue; }
        // The name, not the punctuation that found it: `|disp` refs `disp`, `.eq` refs `eq`.
        const name = rule.whole ? m[0] : m[1];
        const at = m.index + (rule.whole ? 0 : m[0].indexOf(name));
        if (rule.namespace) {
          const kind = NAMESPACES[name];
          if (kind) push(from + at, from + at + name.length, rule.cls, `${kind}:${name}`);
          continue;
        }
        // `const.g` is a constant and `eq.kin` an equation, so neither is a quantity attribute.
        // The name before the dot decides, and an unclaimed `.g` stays ordinary tag text.
        if (rule.notAfterNamespace) {
          const before = /([A-Za-z_]\w*)\.$/.exec(slice.slice(0, at));
          if (before && NAMESPACES[before[1]]) continue;
        }
        push(from + at, from + at + name.length, rule.cls, `${rule.kind}:${name}`);
      }
    }
  }
  // Resolve the overlaps here rather than leaving them to the carving in `highlight`. `d.to('cm')`
  // matches both the attribute rule and the call rule, and which wins is decided by the order of
  // `INNER` -- but only `highlight` was applying that order, so the F1 lookup, which reads this
  // list directly, saw `.to` as a global as well. Two paths, one of them wrong. Applying it once,
  // here, is the only way they can agree by construction.
  const kept = [];
  for (const candidate of found) {
    if (kept.some((k) => candidate.start < k.end && k.start < candidate.end)) continue;
    kept.push(candidate);
  }
  return kept;
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function collectMatches(text, rules) {
  const matches = [];
  rules.forEach((rule, priority) => {
    const re = new RegExp(rule.re.source, rule.re.flags);
    let m;
    while ((m = re.exec(text))) {
      if (m[0].length === 0) { re.lastIndex++; continue; }
      matches.push({ start: m.index, end: m.index + m[0].length, cls: rule.cls, priority });
    }
  });
  // Higher-priority rules (lower index, e.g. Jinja tags) are resolved first, so
  // they always win even when nested inside a lower-priority match (e.g. a
  // `(§ … §)` tag inside `$…$` math) instead of being swallowed by whichever
  // match merely starts earliest.
  matches.sort((a, b) => a.priority - b.priority || a.start - b.start);
  return matches;
}

function highlight(text, lang) {
  const rules = RULES[lang];
  if (!rules) return escapeHtml(text);

  // Priority -1, so a name inside a tag is claimed before the tag rule reaches it and the tag is
  // carved into siblings around it. Nothing new is needed for that: it is the same mechanism that
  // already lets a `(§ … §)` win against the `$…$` it sits inside.
  const matches = collectReferences(text, lang).concat(collectMatches(text, rules))
    .sort((a, b) => a.priority - b.priority || a.start - b.start);
  const claimed = []; // non-overlapping {start, end, cls, ref}, built by carving out claimed ranges

  for (const m of matches) {
    let free = [[m.start, m.end]];
    for (const c of claimed) {
      const next = [];
      for (const [s, e] of free) {
        if (c.end <= s || c.start >= e) { next.push([s, e]); continue; }
        if (c.start > s) next.push([s, c.start]);
        if (c.end < e) next.push([c.end, e]);
      }
      free = next;
    }
    for (const [s, e] of free) {
      // A reference is carried only by a range that survived whole. A name half carved away is no
      // longer that name, and offering its tooltip would point at something that is not there.
      const ref = m.ref && s === m.start && e === m.end ? m.ref : null;
      if (e > s) claimed.push({ start: s, end: e, cls: m.cls, ref });
    }
  }
  claimed.sort((a, b) => a.start - b.start);

  let html = "";
  let cursor = 0;
  for (const c of claimed) {
    if (c.start < cursor) continue;
    html += escapeHtml(text.slice(cursor, c.start));
    const ref = c.ref ? ` data-ref="${escapeHtml(c.ref)}"` : "";
    html += `<span class="${c.cls}"${ref}>${escapeHtml(text.slice(c.start, c.end))}</span>`;
    cursor = c.end;
  }
  html += escapeHtml(text.slice(cursor));
  return html;
}
