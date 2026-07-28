// Minimal dependency-free syntax highlighter for the DGS Markdown+Jinja DSL,
// meta.yaml, and the preamble's `@J` mini-language. No external library —
// just a priority-ordered, non-overlapping regex tokenizer.

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
  "dgs-yaml": [
    { re: /#.*/g, cls: "tok-comment" },
    { re: /'[^'\n]*'|"[^"\n]*"/g, cls: "tok-string" },
    { re: /^\s*-\s*[\w-]+(?=:)/gm, cls: "tok-key" },
    { re: /^\s*[\w-]+(?=:)/gm, cls: "tok-key" },
    { re: /(?<![\w.])-?\d+(\.\d+)?\b/g, cls: "tok-number" },
  ],
  "dgs-preamble": [
    { re: /^@J\b/gm, cls: "tok-keyword" },
    { re: /\bset\b/g, cls: "tok-keyword2" },
    { re: /\bconst\.[\w.]+/g, cls: "tok-const" },
  ],
};

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

  const matches = collectMatches(text, rules);
  const claimed = []; // non-overlapping {start, end, cls}, built by carving out already-claimed ranges

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
      if (e > s) claimed.push({ start: s, end: e, cls: m.cls });
    }
  }
  claimed.sort((a, b) => a.start - b.start);

  let html = "";
  let cursor = 0;
  for (const c of claimed) {
    if (c.start < cursor) continue;
    html += escapeHtml(text.slice(cursor, c.start));
    html += `<span class="${c.cls}">${escapeHtml(text.slice(c.start, c.end))}</span>`;
    cursor = c.end;
  }
  html += escapeHtml(text.slice(cursor));
  return html;
}
