/**
 * The audit page: every volume at a glance, then one volume in detail.
 *
 * No framework and no build step, like `app.js` beside it. The overview is recomputed server-side
 * on every request because a source-only pass over the whole repository costs about a second, so
 * there is nothing here that caches or invalidates.
 */
//: Mirrored from `core/audit/model.py` and `core/audit/status.py`. The server sends these too, and
//: they win when it does -- but hard-coding the defaults means a page served by an older process
//: still renders instead of throwing on the first row it draws.
const DEFAULT_SEVERITIES = ["error", "warning", "info"];
const DEFAULT_STATES = ["broken", "missing", "partial", "ok", "none"];

const state = {
  checks: {},          // id -> {severity, title}
  severities: DEFAULT_SEVERITIES,
  states: DEFAULT_STATES,   // status states, worst first
  overview: [],
  scope: null,         // {module, scope} currently open
  detail: null,        // the last /api/audit/scope response
  hideInfo: true,
  //: 'meta' follows the volume meta's `problems:` list -- the running order, easiest first, and
  //: what the builder iterates. 'alpha' is for finding one problem by name.
  order: "meta",
};

const el = (id) => document.getElementById(id);

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
  return body;
}

function setStatus(text, cls) {
  const s = el("status");
  s.textContent = text;
  s.className = cls || "";
}

function node(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

/* A `th` whose label is an abbreviation, carrying its expansion. The <abbr> holds the title rather
   than the cell, so the dotted underline marks exactly the word that needs explaining. */
function headCell(cls, label, help) {
  const th = node("th", cls);
  if (help) {
    const a = node("abbr", "", label);
    a.title = help;
    th.appendChild(a);
  } else {
    th.textContent = label;
  }
  return th;
}

/** A cell whose value is only worth showing when it is not zero. */
function count(value, cls) {
  const td = node("td", `num ${cls ?? ""}`);
  td.textContent = value ? String(value) : "";
  return td;
}

function ago(seconds) {
  if (!seconds) return "";
  const delta = Date.now() / 1000 - seconds;
  if (delta < 90) return "just now";
  if (delta < 3600) return `${Math.round(delta / 60)} min ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)} h ago`;
  return `${Math.round(delta / 86400)} d ago`;
}

// --- overview ---------------------------------------------------------------

/**
 * The four things that take a volume from converted-on-paper to finished. Named here in the order
 * they are worth reading, with a short column head: the verdict is in the colour and the tooltip.
 */
//: kind, the abbreviation shown in a narrow column, and what that column actually asks.
const STATUS_KINDS = [
  ["translations", "trans",
   "Does every language this volume uses have each file, non-empty \u2014 or a deliberate symlink "
   + "to another language?"],
  ["equations", "eq",
   "Does each display equation live once in meta.yaml's `eq:` and get referenced, instead of being "
   + "written out again in every language?"],
  ["pictures", "pics",
   "Does every figure the Markdown references exist, and is every picture file present actually "
   + "referenced?"],
  ["values", "vals",
   "Do the numbers live in meta.yaml's `values:` and reach the prose through (\u00a7 \u2026 \u00a7), "
   + "rather than being typed into the sentence?"],
];

const SEVERITY_HELP = {
  error: "Something is wrong and will bite: a build failure, a dangling reference, a unit siunitx "
       + "will refuse.",
  warning: "A convention broken, or a difference between languages worth a look.",
  info: "Recorded, not a complaint \u2014 a deliberate symlink, say. Hidden by default.",
};

const BUILD_HELP = "Targets that compiled the last time build checks were run here, and how long "
                 + "ago that was. Blank means never run.";

/* One mark per translated file. The letter says which file, the colour and shape say what state
   it is in, so a nine-language row still fits and still reads. `symlink` is not a fault: an
   unwritten translation mirrors its master rather than keeping a stale copy. */
const TRANSLATION_MARK = {
  ok: { glyph: "", cls: "tr-ok", word: "translated" },
  symlink: { glyph: "\u2192", cls: "tr-symlink", word: "mirrors another language" },
  empty: { glyph: "\u2205", cls: "tr-empty", word: "file exists but is empty" },
  missing: { glyph: "", cls: "tr-missing", word: "no such file" },
};

const TRANSLATION_LEGEND =
  "Capitals are the required files \u2014 P problem, S solution; lower case is optional extra "
  + "content. Bold = translated \u00b7 \u2192 mirrors another language \u00b7 \u2205 empty "
  + "\u00b7 struck through = missing";

/* `problem.md` is P and `solution.md` is S; an extra takes an initial per hyphenated part, so
   `answer-extra.md` is `ae` and `problem-extra.md` is `pe` -- distinct from each other and from
   the two capitals, which a bare first letter would not be. */
function fileMark(name, required) {
  const stem = name.replace(/\.md$/, "");
  if (required) return stem.charAt(0).toUpperCase();
  return stem.split("-").map((part) => part.charAt(0)).join("").toLowerCase();
}

const MARK_LEGEND = "\u2713 ok \u00b7 \u25d1 partial \u00b7 \u2717 missing or broken "
                  + "\u00b7 \u00b7 nothing to do";

/** A short mark per state -- the colour carries the meaning, this keeps it legible without it. */
const STATE_MARK = {
  ok: "\u2713",        // check
  partial: "\u25d1",   // half-filled circle
  missing: "\u2717",   // cross
  broken: "\u2717",
  none: "\u00b7",      // middle dot: nothing to do, not a complaint
};

function statusCell(status) {
  const td = node("td", "num status");
  if (!status) return td;
  td.classList.add(`state-${status.state}`);
  td.textContent = STATE_MARK[status.state] ?? "?";
  td.title = `${status.state}: ${status.summary}`;
  return td;
}

//: label, cell class, how to read the value out of a row, and what the column means.
const OVERVIEW_COLUMNS = [
  ["volume", "", (r) => r.module_label + " " + r.scope,
   "The competition and volume. Click the row to open it."],
  ["problems", "num", (r) => r.problems,
   "Problem directories found under this volume."],
  ["metas", "num", (r) => r.metas_present === r.problems ? "" : `${r.metas_present}/${r.problems}`,
   "Problems with a meta.yaml, shown only when some have none."],
  ["no author", "num", (r) => r.authors_missing,
   "Problems that have an `authors:` block but name nobody in it. An unrecorded author stays "
   + "empty on purpose \u2014 this counts how many are still waiting."],
  ["people", "num", (r) => r.authors,
   "Distinct people credited, across idea, problem and solution. `?` is not counted: it means "
   + "\u201cnot classified\u201d, not a person."],
  ["tags", "num", (r) => r.tags,
   "Distinct tags used in this volume."],
  ["untagged", "num", (r) => r.untagged,
   "Problems carrying no tags at all."],
  ["languages", "num", (r) => r.languages.length,
   "Language directories present anywhere in this volume."],
];

function renderOverview() {
  const table = el("overview-table");
  table.innerHTML = "";

  const head = table.insertRow();
  for (const [label, cls, , help] of OVERVIEW_COLUMNS) head.appendChild(headCell(cls, label, help));
  for (const severity of state.severities) {
    if (severity === "info" && state.hideInfo) continue;
    head.appendChild(headCell(`num sev-${severity}`, severity, SEVERITY_HELP[severity]));
  }
  head.appendChild(headCell(
    "status-strip", "progress",
    "Four verdicts per volume, worst problem wins: "
    + STATUS_KINDS.map(([, label]) => label).join(", ") + ". " + MARK_LEGEND + "."));
  head.appendChild(headCell("", "build", BUILD_HELP));

  for (const row of state.overview) {
    try {
      overviewRow(table, row);
    } catch (e) {
      // A row that cannot be drawn is worth one broken row, not an empty page with no explanation
      console.error("audit: could not draw", row.module, row.scope, e);
      const tr = table.insertRow();
      const td = node("td", "sev-error", `${row.module}/${row.scope}: ${e.message}`);
      td.colSpan = 12;
      tr.appendChild(td);
    }
  }
}

function overviewRow(table, row) {
  {
    const tr = table.insertRow();
    tr.className = "clickable";
    if (state.scope && state.scope.module === row.module && state.scope.scope === row.scope) {
      tr.classList.add("selected");
    }
    tr.addEventListener("click", () => openScope(row.module, row.scope));

    for (const [, cls, get] of OVERVIEW_COLUMNS) {
      const value = get(row);
      tr.appendChild(node("td", cls, value === 0 ? "" : String(value)));
    }
    for (const severity of state.severities) {
      if (severity === "info" && state.hideInfo) continue;
      tr.appendChild(count(row.severity[severity], `sev-${severity}`));
    }

    // Four marks, one per kind, coloured by the worst problem in the volume: the same verdicts the
    // detail table shows per problem, collapsed to something readable in a list of 38.
    const strip = node("td", "status-strip");
    for (const [kind, label] of STATUS_KINDS) {
      const summary = row.status?.[kind];
      if (!summary) continue;
      const mark = node("span", `state-${summary.worst}`, STATE_MARK[summary.worst] ?? "?");
      const counts = state.states
        .filter((s) => summary.counts[s])
        .map((s) => `${summary.counts[s]} ${s}`)
        .join(", ");
      mark.title = `${kind}: ${counts}`;
      strip.appendChild(mark);
    }
    tr.appendChild(strip);

    const build = row.cached_build;
    const cell = node("td", "build-cell");
    if (build) {
      const ok = build.ok === build.total;
      cell.appendChild(node("span", ok ? "pill ok" : "pill bad",
                            `${build.ok}/${build.total}`));
      cell.appendChild(node("span", "hint", " " + ago(build.ran_at)));
    }
    tr.appendChild(cell);
  }
}


// --- one volume -------------------------------------------------------------

async function openScope(module, scope) {
  state.scope = { module, scope };
  // so the page can be linked to and survives a reload
  const hash = `#${module}/${scope}`;
  if (location.hash !== hash) history.replaceState(null, "", hash);
  el("detail-title").textContent = `${module} / ${scope}`;
  el("build-btn").disabled = false;
  el("detail-body").innerHTML = "";
  el("detail-body").appendChild(node("p", "placeholder", "Reading…"));
  renderOverview();
  try {
    state.detail = await fetchJSON(`/api/audit/scope/${module}/${scope}`);
    renderDetail();
    setStatus("");
  } catch (e) {
    console.error(e);
    setStatus(`${module}/${scope}: ${e.message}`, "error");
    el("detail-body").innerHTML = "";
    el("detail-body").appendChild(node("p", "placeholder sev-error", e.message));
  }
}

function visibleFindings() {
  return (state.detail.findings ?? [])
    .filter((f) => !(state.hideInfo && f.severity === "info"));
}

function renderDetail() {
  const body = el("detail-body");
  body.innerHTML = "";
  const d = state.detail;

  renderBuildState(d.build);
  body.appendChild(statsPanels(d.stats));
  body.appendChild(problemTable(d));
  body.appendChild(findingList());
}

function renderBuildState(build) {
  const span = el("build-state");
  if (!build) { span.textContent = "never built"; span.className = "hint"; return; }
  const ok = build.ok === build.total;
  span.className = build.stale ? "hint warn" : "hint";
  span.textContent = `${build.ok}/${build.total} targets ${ok ? "built" : "built"}`
    + ` · ${ago(build.ran_at)}`
    + (build.stale ? " · sources have changed since" : "");
}

/** The four statistics panels: authors, tags, languages, templating. */
function statsPanels(stats) {
  const wrap = node("div", "panels");

  const authors = panel("Authors", `${stats.authors.length} people`
    + (stats.authors_missing ? `, ${stats.authors_missing} problems record nobody` : ""));
  if (stats.authors.length) {
    const t = node("table", "grid compact");
    const head = t.insertRow();
    for (const h of ["", "idea", "problem", "solution"]) head.appendChild(node("th", "num", h));
    for (const person of stats.authors) {
      const tr = t.insertRow();
      tr.appendChild(node("td", "", person.name));
      for (const role of ["idea", "problem", "solution"]) {
        tr.appendChild(count(person[role] ?? 0));
      }
    }
    authors.appendChild(t);
  }
  wrap.appendChild(authors);

  const tags = panel("Tags", `${stats.tags.length} distinct`
    + (stats.untagged ? `, ${stats.untagged} untagged` : ""));
  if (stats.tags.length) {
    const most = stats.tags[0][1];
    const list = node("div", "bars");
    for (const [tag, n] of stats.tags) {
      const row = node("div", "bar-row");
      row.appendChild(node("span", "bar-label", tag));
      const track = node("span", "bar-track");
      const fill = node("span", "bar-fill");
      fill.style.width = `${Math.round((n / most) * 100)}%`;
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(node("span", "bar-count", String(n)));
      list.appendChild(row);
    }
    tags.appendChild(list);
  }
  wrap.appendChild(tags);

  const langs = panel("Files by language", "");
  if (stats.language_list.length) {
    const t = node("table", "grid compact");
    const head = t.insertRow();
    head.appendChild(node("th", "", ""));
    for (const kind of stats.file_kinds) {
      head.appendChild(node("th", "num", kind.replace(/\.md$/, "")));
    }
    for (const lang of stats.language_list) {
      const tr = t.insertRow();
      tr.appendChild(node("td", "", lang));
      for (const kind of stats.file_kinds) {
        tr.appendChild(count(stats.languages[lang]?.[kind] ?? 0));
      }
    }
    langs.appendChild(t);
  }
  if (Object.keys(stats.shared ?? {}).length) {
    // Files beside the unit rather than in a language directory -- `answer.md` and its variants.
    // Listed apart from the matrix because they belong to no language.
    const shared = node("table", "grid compact");
    const head = shared.insertRow();
    head.appendChild(node("th", "", "shared"));
    head.appendChild(node("th", "num", ""));
    for (const kind of stats.shared_kinds) {
      const tr = shared.insertRow();
      tr.appendChild(node("td", "", kind.replace(/\.md$/, "")));
      tr.appendChild(node("td", "num", String(stats.shared[kind])));
    }
    langs.appendChild(shared);
  }
  wrap.appendChild(langs);

  const progress = panel("Progress", "");
  if (state.detail?.status_summary) {
    const t = node("table", "grid compact");
    const head = t.insertRow();
    head.appendChild(node("th", "", ""));
    for (const s of state.states) head.appendChild(node("th", `num state-${s}`, s));
    for (const [kind] of STATUS_KINDS) {
      const summary = state.detail.status_summary[kind];
      if (!summary) continue;
      const tr = t.insertRow();
      tr.appendChild(node("td", "", kind));
      for (const s of state.states) {
        const cell = count(summary.counts[s] ?? 0, `state-${s}`);
        tr.appendChild(cell);
      }
    }
    progress.appendChild(t);
  }
  wrap.appendChild(progress);

  const tmpl = panel("Templating", "");
  const t = node("table", "grid compact");
  for (const block of ["values", "derived", "eq"]) {
    const tr = t.insertRow();
    tr.appendChild(node("td", "", block));
    tr.appendChild(node("td", "num", String(stats.templating[block] ?? 0)));
    tr.appendChild(node("td", "hint",
                        `${stats.templating[block + "_entries"] ?? 0} entries`));
  }
  tmpl.appendChild(t);
  wrap.appendChild(tmpl);

  return wrap;
}

function panel(title, subtitle, control) {
  const p = node("section", "panel");
  const h = node("div", "panel-head");
  h.appendChild(node("strong", "", title));
  if (subtitle) h.appendChild(node("span", "hint", subtitle));
  if (control) {
    h.appendChild(node("span", "spacer"));
    h.appendChild(control);
  }
  p.appendChild(h);
  return p;
}

/* The order toggle. The volume meta's list is the competition's own running order, so it is the
   default; the alphabet is what you want when you know the name and not the number. */
function orderControl() {
  const wrap = node("span", "order-control");
  wrap.appendChild(node("span", "hint", "order"));
  const select = node("select", "");
  for (const [value, label, help] of [
    ["meta", "as in meta.yaml", "The volume's `problems:` list \u2014 the running order, and what "
                               + "the builder iterates."],
    ["alpha", "alphabetical", "By problem id."],
  ]) {
    const opt = node("option", "", label);
    opt.value = value;
    opt.title = help;
    if (state.order === value) opt.selected = true;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => {
    state.order = select.value;
    renderDetail();
  });
  wrap.appendChild(select);
  return wrap;
}

/* Units come from the server in meta order, with anything the meta omits last. Sorting here rather
   than re-fetching: the order is a view of the same data, not a different question to ask. */
function orderedUnits(d) {
  const units = [...d.units];
  if (state.order === "alpha") units.sort((a, b) => a.problem.localeCompare(b.problem));
  return units;
}

/** The big table: one row per problem. */
/* What this problem has in one language, file by file: which files are translated, which are
   empty, which are missing, and which mirror another language. The verdict in the `trans` column
   is the same data collapsed to one mark; this is the column that says why. */
function translationCell(d, unit, lang) {
  const td = node("td", "lang trans-cell");
  const info = unit.status?.translations?.detail?.languages?.[lang];
  const files = unit.status?.translations?.detail?.order
             ?? d.translated_files ?? ["problem.md", "solution.md"];

  if (!info) {
    td.textContent = "\u00b7";
    td.className += " absent";
    td.title = `${lang}: nothing recorded`;
    return td;
  }
  if (!info.files) {
    // the whole language directory is absent -- one dash, not one per file
    td.textContent = "\u2014";
    td.className += " absent";
    td.title = `${lang}: ${info.note || "no directory"}`;
    return td;
  }

  const words = [];
  for (const name of files) {
    const entry = info.files[name];
    const state = entry?.state ?? "missing";
    const mark = TRANSLATION_MARK[state] ?? TRANSLATION_MARK.missing;
    const required = entry?.required ?? true;
    const cls = `trans-mark ${mark.cls}${required ? "" : " trans-optional"}`;
    const span = node("span", cls, fileMark(name, required) + mark.glyph);
    span.title = `${name}: ${entry?.note || mark.word}`;
    td.appendChild(span);
    words.push(`${name} ${entry?.note || mark.word}`);
  }
  td.title = `${lang} \u2014 ${words.join("; ")}`;
  return td;
}


function problemTable(d) {
  const byUnit = {};
  for (const f of visibleFindings()) {
    if (f.unit) (byUnit[f.unit] ??= []).push(f);
  }

  const section = panel("Problems", `${d.units.length}`, orderControl());
  const t = node("table", "grid");
  const head = t.insertRow();
  head.appendChild(headCell("num", "#",
                            "Position in the volume meta's `problems:` list, which is the order the "
                            + "problems are set in. Blank means the list does not name it."));
  for (const h of ["problem", "tags", "authors"]) head.appendChild(node("th", "", h));
  for (const [kind, label, help] of STATUS_KINDS) {
    head.appendChild(headCell("num status", label, `${kind} \u2014 ${help} ${MARK_LEGEND}.`));
  }
  for (const lang of d.stats.language_list) {
    const name = d.stats.language_names?.[lang] ?? lang;
    head.appendChild(headCell("lang", lang, `${name}. ${TRANSLATION_LEGEND}.`));
  }
  head.appendChild(headCell("", "findings", "What the checks reported for this problem."));

  for (const unit of orderedUnits(d)) {
    const tr = t.insertRow();

    // The competition number, and a visible mark when the volume meta does not list the problem at
    // all -- that one is not in the competition, however complete its sources look.
    if (unit.order === null || unit.order === undefined) {
      const nocell = node("td", "num absent", "\u2014");
      nocell.title = "not listed in the volume meta, so it is never built";
      tr.appendChild(nocell);
      tr.classList.add("unlisted");
    } else {
      tr.appendChild(node("td", "num", String(unit.order + 1)));
    }

    const first = node("td", "");
    // the whole point of living in the same app: click through to the problem in the editor
    const link = node("a", "", unit.problem);
    link.href = `/#${d.module}/${unit.unit}`;
    link.title = "open in the editor";
    first.appendChild(link);
    tr.appendChild(first);

    tr.appendChild(node("td", "tags", (unit.tags ?? []).join(" ")));

    const authors = unit.authors
      ? ["idea", "problem", "solution"].flatMap((r) => unit.authors[r] ?? [])
      : [];
    tr.appendChild(node("td", "", [...new Set(authors)].join(", ")));
    for (const [kind] of STATUS_KINDS) tr.appendChild(statusCell(unit.status?.[kind]));

    for (const lang of d.stats.language_list) {
      tr.appendChild(translationCell(d, unit, lang));
    }

    const cell = node("td", "findings-cell");
    for (const f of byUnit[unit.unit] ?? []) {
      const pill = node("span", `pill sev-${f.severity}`, f.check);
      pill.title = `${f.where ? f.where + " — " : ""}${f.message}`;
      cell.appendChild(pill);
    }
    tr.appendChild(cell);
  }
  section.appendChild(t);
  return section;
}

/** Findings grouped by check, so a whole class can be read at once. */
function findingList() {
  const findings = visibleFindings();
  const grouped = {};
  for (const f of findings) (grouped[f.check] ??= []).push(f);

  const order = Object.keys(grouped).sort((a, b) => {
    const sa = state.severities.indexOf(state.checks[a]?.severity ?? "info");
    const sb = state.severities.indexOf(state.checks[b]?.severity ?? "info");
    return sa - sb || grouped[b].length - grouped[a].length;
  });

  const section = panel("Findings", `${findings.length}`);
  if (!findings.length) {
    section.appendChild(node("p", "hint", "Nothing to report."));
    return section;
  }
  for (const check of order) {
    const group = grouped[check];
    const details = node("details", "finding-group");
    const summary = node("summary", "");
    summary.appendChild(node("span", `pill sev-${group[0].severity}`, check));
    summary.appendChild(node("span", "", ` ${state.checks[check]?.title ?? ""}`));
    summary.appendChild(node("span", "hint", ` · ${group.length}`));
    details.appendChild(summary);
    const list = node("ul", "finding-items");
    for (const f of group) {
      const li = node("li", "");
      if (f.problem) li.appendChild(node("strong", "", f.problem + " "));
      if (f.where) li.appendChild(node("span", "hint", f.where + (f.line ? `:${f.line}` : "") + " "));
      li.appendChild(node("span", "", f.message));
      list.appendChild(li);
    }
    details.appendChild(list);
    section.appendChild(details);
  }
  return section;
}

// --- build checks -----------------------------------------------------------

async function runBuildChecks() {
  if (!state.scope) return;
  const { module, scope } = state.scope;
  el("build-btn").disabled = true;
  setStatus("building — this takes minutes", "busy");
  try {
    const build = await fetchJSON(`/api/audit/build/${module}/${scope}`, { method: "POST" });
    state.detail.build = build;
    renderBuildState(build);
    renderDetail();
    await loadOverview();
    setStatus(`${build.ok}/${build.total} targets built in ${build.duration}s`,
              build.ok === build.total ? "ok" : "error");
  } catch (e) {
    setStatus(e.message, "error");
  } finally {
    el("build-btn").disabled = false;
  }
}

// --- layout -----------------------------------------------------------------

const OVERVIEW_HEIGHT_KEY = "dgs-audit-overview-height";

/**
 * The gutter between the volume list and the detail. Same shape as the editor's resizers: the CSS
 * custom property is the single source of truth, shared by the grid template and the drag, and the
 * last size is remembered so the page opens the way you left it.
 */
function wireResizer() {
  const resizer = el("audit-resizer");
  const grid = el("audit-main");
  let dragging = false;

  const saved = localStorage.getItem(OVERVIEW_HEIGHT_KEY);
  if (saved) grid.style.setProperty("--overview-height", saved);

  resizer.addEventListener("mousedown", (e) => {
    dragging = true;
    resizer.classList.add("dragging");
    e.preventDefault();
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = grid.getBoundingClientRect();
    const height = Math.min(Math.max(e.clientY - rect.top, 80), rect.height - 120);
    grid.style.setProperty("--overview-height", `${height}px`);
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    resizer.classList.remove("dragging");
    localStorage.setItem(OVERVIEW_HEIGHT_KEY,
                         grid.style.getPropertyValue("--overview-height"));
  });
}

// --- boot -------------------------------------------------------------------

async function loadOverview() {
  const rows = await fetchJSON("/api/audit/overview");
  state.overview = rows;
  renderOverview();
}

/**
 * Show every error somewhere a person will see it.
 *
 * Without this an exception anywhere leaves the page looking merely inert -- the table draws, or
 * does not, and clicking achieves nothing with no hint as to why. A tool that fails silently costs
 * more to diagnose than it ever saved.
 */
function wireErrorReporting() {
  window.addEventListener("error", (e) => {
    setStatus(`script error: ${e.message}`, "error");
    console.error(e.error ?? e.message);
  });
  window.addEventListener("unhandledrejection", (e) => {
    setStatus(`failed: ${e.reason?.message ?? e.reason}`, "error");
    console.error(e.reason);
  });
}

async function boot() {
  wireErrorReporting();
  wireResizer();
  el("refresh-btn").addEventListener("click", () => refresh());
  el("build-btn").addEventListener("click", runBuildChecks);
  el("hide-info").addEventListener("change", (e) => {
    state.hideInfo = e.target.checked;
    renderOverview();
    if (state.detail) renderDetail();
  });
  window.addEventListener("hashchange", openFromHash);
  await refresh();
}

async function refresh() {
  setStatus("reading…", "busy");
  try {
    const meta = await fetchJSON("/api/audit/checks");
    state.severities = meta.severities ?? DEFAULT_SEVERITIES;
    state.states = meta.states ?? DEFAULT_STATES;
    state.checks = Object.fromEntries(meta.checks.map((c) => [c.id, c]));
    await loadOverview();
    setStatus("");
    await openFromHash();
  } catch (e) {
    setStatus(e.message, "error");
  }
}

/** `#naboj/phys/28` opens that volume, so a page can be linked to and reloaded. */
async function openFromHash() {
  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (!hash) return;
  const row = state.overview.find((r) => hash === `${r.module}/${r.scope}`);
  if (row) await openScope(row.module, row.scope);
}

boot();
