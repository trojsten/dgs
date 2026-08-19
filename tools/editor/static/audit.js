/**
 * The audit page: every volume at a glance, then one volume in detail.
 *
 * No framework and no build step, like `app.js` beside it. The overview is recomputed server-side
 * on every request because a source-only pass over the whole repository costs about a second, so
 * there is nothing here that caches or invalidates.
 */
const state = {
  checks: {},          // id -> {severity, title}
  severities: [],
  overview: [],
  scope: null,         // {module, scope} currently open
  detail: null,        // the last /api/audit/scope response
  hideInfo: true,
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

const OVERVIEW_COLUMNS = [
  ["volume", "", (r) => r.module_label + " " + r.scope],
  ["problems", "num", (r) => r.problems],
  ["metas", "num", (r) => r.metas_present === r.problems ? "" : `${r.metas_present}/${r.problems}`],
  ["no author", "num", (r) => r.authors_missing],
  ["people", "num", (r) => r.authors],
  ["tags", "num", (r) => r.tags],
  ["untagged", "num", (r) => r.untagged],
  ["languages", "num", (r) => r.languages.length],
];

function renderOverview() {
  const table = el("overview-table");
  table.innerHTML = "";

  const head = table.insertRow();
  for (const [label, cls] of OVERVIEW_COLUMNS) head.appendChild(node("th", cls, label));
  for (const severity of state.severities) {
    if (severity === "info" && state.hideInfo) continue;
    head.appendChild(node("th", `num sev-${severity}`, severity));
  }
  head.appendChild(node("th", "", "build"));

  for (const row of state.overview) {
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
    setStatus(e.message, "error");
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

function panel(title, subtitle) {
  const p = node("section", "panel");
  const h = node("div", "panel-head");
  h.appendChild(node("strong", "", title));
  if (subtitle) h.appendChild(node("span", "hint", subtitle));
  p.appendChild(h);
  return p;
}

/** The big table: one row per problem. */
function problemTable(d) {
  const byUnit = {};
  for (const f of visibleFindings()) {
    if (f.unit) (byUnit[f.unit] ??= []).push(f);
  }

  const section = panel("Problems", `${d.units.length}`);
  const t = node("table", "grid");
  const head = t.insertRow();
  for (const h of ["problem", "tags", "authors", "values", "eq"]) {
    head.appendChild(node("th", "", h));
  }
  for (const lang of d.stats.language_list) {
    head.appendChild(node("th", "num lang", lang));
  }
  head.appendChild(node("th", "", "findings"));

  for (const unit of d.units) {
    const tr = t.insertRow();
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
    tr.appendChild(count(unit.templating.values));
    tr.appendChild(count(unit.templating.eq));

    for (const lang of d.stats.language_list) {
      const files = unit.files[lang];
      const td = node("td", "num lang");
      if (!files) {
        td.textContent = "·";
        td.className += " absent";
        td.title = "no directory for this language";
      } else {
        td.textContent = String(files.length);
        td.title = files.join(", ");
      }
      tr.appendChild(td);
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

async function boot() {
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
    state.severities = meta.severities;
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
