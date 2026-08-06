const state = {
  modules: [],        // [{name, label, languages, units: [...]}]
  module: null,       // the selected module's descriptor
  unit: null,         // path of the open unit, relative to source/<module>
  lang: null,
  targets: [],        // every file this problem/language actually has, in document order
  activeTarget: null,
  buffers: {},        // target -> current text
  baseline: {},       // target -> last-written text (for dirty tracking)
  meta: "",
  metaBaseline: "",
  activeOutput: "pdf",
  pdfUrl: null,       // currently displayed PDF, or null when nothing is compiled
  log: "",
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

function isDirty(target) {
  return (state.buffers[target] ?? "") !== (state.baseline[target] ?? "");
}

function metaDirty() {
  return state.meta !== state.metaBaseline;
}

function anyDirty() {
  return metaDirty() || state.targets.some(isDirty);
}

// --- syntax highlighting overlay -------------------------------------------

function refreshHighlight(textareaId, highlightId, lang) {
  const text = el(textareaId).value;
  el(highlightId).innerHTML = highlight(text + "\n", typeof lang === "function" ? lang() : lang);
}

function wireCodeEditor(textareaId, highlightId, lang, onInput) {
  const textarea = el(textareaId);
  const pre = el(highlightId).parentElement;
  textarea.addEventListener("input", () => {
    refreshHighlight(textareaId, highlightId, lang);
    if (onInput) onInput();
  });
  textarea.addEventListener("scroll", () => {
    pre.scrollTop = textarea.scrollTop;
    pre.scrollLeft = textarea.scrollLeft;
  });
}

function setEditorValue(textareaId, highlightId, lang, value) {
  el(textareaId).value = value;
  refreshHighlight(textareaId, highlightId, lang);
}

// --- source tabs -----------------------------------------------------------

const TARGET_LABELS = {
  "problem": "Problem",
  "problem-extra": "Problem extra",
  "solution": "Solution",
  "answer": "Answer",
  "answer-extra": "Answer extra",
  "answer-also": "Answer also",
  "answer-interval": "Answer interval",
};

function labelFor(target) {
  return TARGET_LABELS[target] || target;
}

// A gnuplot script or its data table, carried as a path rather than one of the seven prose names.
function isAux(target) {
  return target != null && !(target in TARGET_LABELS);
}

// The .md grammar would read a gnuplot script's `#` comments as headings and its `$1` columns
// as maths, so aux files get their own mode -- one that still lights up the `(§ … §)` tags.
function sourceMode() {
  return isAux(state.activeTarget) ? "dgs-gnuplot" : "dgs-md";
}

function syncActionsForTarget() {
  el("compile-btn").disabled = !state.hasPreview;
  const aux = isAux(state.activeTarget);
  el("render-btn").disabled = aux && !state.activeTarget.endsWith(".gp");
  document.querySelector('[data-output="lint"]').disabled = aux;
}

function renderSourceTabs() {
  const bar = el("source-tabs");
  bar.innerHTML = "";
  for (const target of state.targets) {
    const btn = document.createElement("button");
    btn.className = "tab" + (target === state.activeTarget ? " active" : "");
    if (isDirty(target)) btn.classList.add("dirty");
    btn.textContent = labelFor(target);
    btn.dataset.target = target;
    btn.addEventListener("click", () => switchTarget(target));
    bar.appendChild(btn);
  }
}

function switchTarget(target) {
  // Keep whatever is in the textarea before swapping it out, or edits to the tab being
  // left behind would be lost.
  if (state.activeTarget) {
    state.buffers[state.activeTarget] = el("source-editor").value;
    rememberScroll();
  }
  state.activeTarget = target;
  setEditorValue("source-editor", "source-highlight", sourceMode, state.buffers[target] ?? "");
  renderSourceTabs();
  syncActionsForTarget();
  if (target) restoreScroll(target);
  writeLocation();
}

// --- where you were ---------------------------------------------------------

/**
 * The address bar is the workspace. `#phys/28/problems/leaky-graph/sk/time.gp` names exactly one
 * open file, so a reload comes back to it, and the URL can be bookmarked or pasted to a colleague.
 *
 * A problem key is always four segments (`<competition>/<volume>/problems/<id>`) and a language
 * never contains a slash, so the rest is the file -- which lets an auxiliary target keep its own
 * `sk/data.dat` shape without any escaping.
 */
function readLocation() {
  const raw = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  if (!raw) return {};
  const slash = raw.indexOf("/");
  if (slash < 0) return {};
  const moduleName = raw.slice(0, slash);
  const module = state.modules.find((m) => m.name === moduleName);
  if (!module) return {};

  // Units are four segments deep in one module and five in another, and scholar has both, so
  // there is no fixed offset to slice at. Take the longest unit that prefixes the rest.
  const tail = raw.slice(slash + 1);
  const unit = module.units
    .filter((u) => tail === u || tail.startsWith(u + "/"))
    .sort((a, b) => b.length - a.length)[0];
  if (!unit) return { module: moduleName };

  const rest = tail.slice(unit.length).replace(/^\//, "").split("/").filter(Boolean);
  return {
    module: moduleName,
    unit,
    lang: module.languages ? (rest.shift() ?? null) : null,
    target: rest.join("/") || null,
  };
}

// `replaceState`, not `pushState`: switching tabs should not fill the history with entries that
// send you back to a different file when you meant to leave the page.
function writeLocation() {
  if (!state.module || !state.unit) return;
  const path = [state.module.name, state.unit, state.lang, state.activeTarget]
    .filter(Boolean).join("/");
  history.replaceState(null, "", `#${path}`);
}

const SCROLL_KEY = "dgs-editor-scroll";

function scrollStore() {
  try {
    return JSON.parse(localStorage.getItem(SCROLL_KEY)) || {};
  } catch {
    return {};
  }
}

function scrollId(target) {
  return `${state.module?.name}/${state.unit}/${state.lang}/${target}`;
}

function rememberScroll() {
  if (!state.unit || !state.activeTarget) return;
  const store = scrollStore();
  store[scrollId(state.activeTarget)] = el("source-editor").scrollTop;
  localStorage.setItem(SCROLL_KEY, JSON.stringify(store));
}

function restoreScroll(target) {
  const top = scrollStore()[scrollId(target)] ?? 0;
  const textarea = el("source-editor");
  textarea.scrollTop = top;
  el("source-highlight").parentElement.scrollTop = top;
}

// --- picker -----------------------------------------------------------------

function fillSelect(selectEl, values, labelFn) {
  selectEl.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = labelFn ? labelFn(v) : v;
    selectEl.appendChild(opt);
  }
}

/**
 * The module's units as a tree, so the picker can offer one select per path level.
 *
 * A node may be both a unit and a parent of units -- a scholar handout has its own `text.md` and
 * a directory per problem -- so `isUnit` is a flag on the node rather than a property of leaves.
 */
function unitTree(units) {
  const root = { children: {}, isUnit: false };
  for (const unit of units) {
    let node = root;
    for (const segment of unit.split("/")) {
      node = (node.children[segment] ??= { children: {}, isUnit: false });
    }
    node.isUnit = true;
  }
  return root;
}

const SELF = "\u00b7";   // the option standing for "this node itself", where it is also a unit

/**
 * Rebuild the cascade of selects for `unit`, one per level, and return nothing: the selects
 * drive everything through their change handlers.
 *
 * Every level gets a select except those the server reports as no choice at all, which is a
 * property of the descriptor rather than of what is checked out: seminar has repositories
 * besides FKS, and hiding the competition because only FKS is cloned would give no hint that
 * the others exist.
 */
function renderCascade(unit) {
  const container = el("unit-cascade");
  container.innerHTML = "";
  if (!state.module) return;

  const segments = unit ? unit.split("/") : [];
  const hidden = new Set(state.module.hidden_levels ?? []);
  const names = Object.fromEntries(state.module.levels ?? []);
  let node = unitTree(state.module.units);
  const prefix = [];

  for (let depth = 0; node && Object.keys(node.children).length; depth++) {
    const options = Object.keys(node.children).sort();
    if (node.isUnit) options.unshift(SELF);

    const chosen = options.includes(segments[depth]) ? segments[depth]
                 : (node.isUnit && depth === segments.length ? SELF : options[0]);

    if (!hidden.has(depth)) {
      const select = document.createElement("select");
      fillSelect(select, options);
      select.value = chosen;
      if (names[depth]) select.title = names[depth];
      const at = [...prefix];
      select.addEventListener("change", (e) => onCascadeChange(at, e.target.value));
      container.appendChild(select);
    }

    if (chosen === SELF) break;
    prefix.push(chosen);
    node = node.children[chosen];
  }
}

/** Descend from `prefix`/`choice`, taking the first option at every level below it. */
function firstUnitUnder(prefix, choice) {
  if (choice === SELF) return prefix.join("/");
  const path = [...prefix, choice];
  let node = unitTree(state.module.units);
  for (const segment of path) node = node.children[segment];
  while (node && !node.isUnit && Object.keys(node.children).length) {
    const next = Object.keys(node.children).sort()[0];
    path.push(next);
    node = node.children[next];
  }
  return path.join("/");
}

async function onCascadeChange(prefix, choice) {
  if (!confirmDiscard()) { renderCascade(state.unit); return; }
  await openUnit(state.module.name, firstUnitUnder(prefix, choice));
}

async function onModuleChange(name) {
  if (!confirmDiscard()) { el("module-select").value = state.module.name; return; }
  const module = state.modules.find((m) => m.name === name);
  if (!module || !module.units.length) return;
  state.module = module;
  await openUnit(name, module.units[0]);
}

async function onLangChange(lang) {
  if (!confirmDiscard()) { el("lang-select").value = state.lang; return; }
  await openUnit(state.module.name, state.unit, lang);
}

async function loadModules() {
  state.modules = await fetchJSON("/api/modules");
  if (!state.modules.length) return;
  fillSelect(el("module-select"), state.modules.map((m) => m.name),
             (n) => state.modules.find((m) => m.name === n).label);

  // Reopen whatever the address bar names, falling back to the first unit of the first module.
  const wanted = readLocation();
  const module = state.modules.find((m) => m.name === wanted.module) ?? state.modules[0];
  const unit = module.units.includes(wanted.unit) ? wanted.unit : module.units[0];
  state.module = module;
  if (unit) await openUnit(module.name, unit, wanted.lang, wanted.target);
}

function confirmDiscard() {
  return !anyDirty() || confirm("Discard unsaved changes?");
}

async function openUnit(moduleName, unit, lang, target) {
  rememberScroll();   // still pointing at the outgoing file
  const query = lang ? `?lang=${encodeURIComponent(lang)}` : "";
  const data = await fetchJSON(`/api/unit/${moduleName}/${unit}${query}`);

  state.module = state.modules.find((m) => m.name === moduleName);
  state.unit = unit;
  state.lang = data.lang;
  state.targets = data.targets;
  state.hasPreview = data.has_preview;
  state.activeTarget = null;

  state.meta = data.meta_yaml ?? "";
  state.metaBaseline = state.meta;
  state.buffers = {};
  for (const t of state.targets) state.buffers[t] = data.files[t] ?? "";
  state.baseline = { ...state.buffers };

  el("module-select").value = moduleName;
  renderCascade(unit);
  const langSelect = el("lang-select");
  langSelect.hidden = !data.langs.length;
  fillSelect(langSelect, data.langs);
  if (data.lang) langSelect.value = data.lang;

  setEditorValue("meta-editor", "meta-highlight", "dgs-yaml", state.meta);
  el("meta-label").textContent =
    data.meta_yaml === null ? "meta.yaml (does not exist yet)" : "meta.yaml";
  switchTarget(state.targets.includes(target) ? target : (state.targets[0] ?? null));
  setStatus("Loaded", "ok");

  el("output-rendered-code").innerHTML = "";
  el("output-rendered").classList.remove("error");
  setLog("");
  // The compiled page outlives the browser session, so a reload gets it straight back rather
  // than an empty pane and a pointless recompile.
  showPdf(data.has_pdf ? pdfUrlFor() : null);
  writeLocation();
}

// --- writing back ----------------------------------------------------------

function captureEditors() {
  if (state.activeTarget) state.buffers[state.activeTarget] = el("source-editor").value;
  state.meta = el("meta-editor").value;
}

/**
 * Only dirty buffers go over the wire. Writing every file on every compile would bump
 * their mtimes and make `make` redo the whole problem each time instead of just the part
 * that changed.
 */
function dirtyFiles() {
  const files = {};
  if (metaDirty()) files.meta_yaml = state.meta;
  const targets = {};
  for (const target of state.targets) {
    if (isDirty(target)) targets[target] = state.buffers[target];
  }
  if (Object.keys(targets).length) files.targets = targets;
  return files;
}

function markSaved() {
  state.baseline = { ...state.buffers };
  state.metaBaseline = state.meta;
  renderSourceTabs();
}

async function post(url, extra) {
  captureEditors();
  return fetchJSON(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ module: state.module.name, unit: state.unit, lang: state.lang,
                           files: dirtyFiles(), ...extra }),
  });
}

async function doSave() {
  if (!state.unit) return;
  setStatus("Saving…", "dirty");
  try {
    const body = await post("/api/save");
    if (body.ok) {
      markSaved();
      setStatus("Saved", "ok");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

// --- output pane -----------------------------------------------------------

function setLog(text) {
  state.log = text;
  el("output-log-code").textContent = text;
}

function logOf(body) {
  // The summary goes on top: the line that says what is wrong is otherwise the second-to-last
  // of a few hundred, under a pretty-printed schema or a TeX package banner.
  const head = body.summary ? `${body.summary}\n\n` : "";
  return `${head}$ ${body.command}\n\n${body.stdout}${body.stderr}`;
}

function failureStatus(body, verb) {
  if (body.summary) return body.summary;
  return body.returncode === null ? `Cannot ${verb}` : `${verb} failed (exit ${body.returncode})`;
}

/**
 * Point the preview at `url`, or clear it when `url` is null.
 *
 * When only the content changed, reload in place rather than reassigning `src`: the
 * browser's PDF viewer keeps its scroll position across a reload but always jumps back to
 * page one when the src changes. It can throw if the viewer refuses to expose its window,
 * so fall back to the src swap.
 */
function showPdf(url, { stale = false } = {}) {
  const frame = el("pdf-frame");
  const placeholder = el("pdf-placeholder");
  const wrapper = el("output-pdf");
  const link = el("pdf-newtab");

  wrapper.classList.toggle("stale", stale);

  if (!url) {
    state.pdfUrl = null;
    frame.classList.remove("loaded");
    frame.removeAttribute("src");
    placeholder.hidden = false;
    placeholder.textContent = "Nothing compiled yet — press Ctrl/Cmd+Enter.";
    link.removeAttribute("href");
    return;
  }

  const sameDocument = state.pdfUrl === url;
  state.pdfUrl = url;
  link.href = url;
  placeholder.hidden = true;
  frame.classList.add("loaded");

  // A failed compile did not rewrite the cached file, so there is nothing to refetch --
  // reloading would only throw away the reader's scroll position for no reason.
  if (stale && sameDocument) return;

  if (sameDocument) {
    try {
      frame.contentWindow.location.reload();
      return;
    } catch {
      // fall through to the src swap
    }
  }
  frame.src = url;
}

function switchOutputTab(name) {
  state.activeOutput = name;
  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.output === name);
  });
  el("output-pdf").hidden = name !== "pdf";
  el("output-rendered").hidden = name !== "rendered";
  el("output-lint").hidden = name !== "lint";
  el("output-log").hidden = name !== "log";
  if (name === "lint") doLint();
}

// --- actions ---------------------------------------------------------------

/**
 * `#pagemode=none` keeps the viewer's outline sidebar shut. hyperref marks the document
 * `/UseOutlines`, so without it PDF.js opens the sidebar over the first page every time.
 */
function pdfUrlFor() {
  const query = state.lang ? `?lang=${encodeURIComponent(state.lang)}` : "";
  return `/api/pdf/${state.module.name}/${state.unit}${query}#pagemode=none`;
}

async function doCompile() {
  if (!state.unit) return;
  setStatus("Compiling…", "dirty");
  try {
    const body = await post("/api/compile");
    setLog(logOf(body));
    markSaved();

    if (body.ok) {
      showPdf(pdfUrlFor());
      switchOutputTab("pdf");
      setStatus("Compiled", "ok");
    } else {
      // Keep the last good render on screen, badged as out of date, and show why.
      if (body.has_pdf) showPdf(state.pdfUrl ?? pdfUrlFor(), { stale: true });
      switchOutputTab("log");
      setStatus(failureStatus(body, "compile"), "error");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function doRender() {
  if (!state.unit || !state.activeTarget) return;
  setStatus("Rendering…", "dirty");
  try {
    const body = await post("/api/render", { target: state.activeTarget });
    setLog(logOf(body));
    markSaved();

    const out = el("output-rendered");
    const code = el("output-rendered-code");
    switchOutputTab("rendered");
    if (body.ok) {
      code.innerHTML = highlight(body.rendered_md ?? "", "dgs-md");
      out.classList.remove("error");
      setStatus("Rendered OK", "ok");
    } else {
      code.textContent = logOf(body);
      out.classList.add("error");
      setStatus(failureStatus(body, "render"), "error");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function doLint() {
  if (!state.unit || !state.activeTarget) return;
  const box = el("output-lint");
  box.textContent = "Linting…";
  try {
    const body = await fetchJSON("/api/lint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ module: state.module.name, unit: state.unit,
                             lang: state.lang, target: state.activeTarget }),
    });
    box.innerHTML = "";
    if (!body.violations.length) {
      box.textContent = "No violations found.";
      return;
    }
    for (const v of body.violations) {
      const div = document.createElement("div");
      div.className = "lint-violation";
      const loc = document.createElement("span");
      loc.className = "loc";
      loc.textContent = `line ${v.line}${v.column !== null ? ":" + v.column : ""}`;
      div.appendChild(loc);
      div.appendChild(document.createTextNode(v.message));
      box.appendChild(div);
    }
  } catch (e) {
    box.textContent = e.message;
  }
}

// --- auto-compile ----------------------------------------------------------

const AUTOCOMPILE_KEY = "dgs-editor-autocompile";
const AUTOCOMPILE_IDLE_MS = 2000;
let autocompileTimer = null;

function scheduleAutocompile() {
  if (!el("autocompile").checked) return;
  clearTimeout(autocompileTimer);
  autocompileTimer = setTimeout(() => {
    if (anyDirty()) doCompile();
  }, AUTOCOMPILE_IDLE_MS);
}

// --- resizers --------------------------------------------------------------

const CONTEXT_HEIGHT_KEY = "dgs-editor-context-height";
const SOURCE_WIDTH_KEY = "dgs-editor-source-width";

/**
 * Wire one draggable gutter. `measure` turns a pointer position into the new CSS value;
 * the property is the single source of truth shared by the grid template and the drag.
 */
function wireResizer(resizerId, property, storageKey, measure) {
  const resizer = el(resizerId);
  const grid = el("grid");
  let dragging = false;

  const saved = localStorage.getItem(storageKey);
  if (saved) grid.style.setProperty(property, saved);

  resizer.addEventListener("mousedown", (e) => {
    dragging = true;
    resizer.classList.add("dragging");
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    grid.style.setProperty(property, measure(e, grid.getBoundingClientRect()));
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    resizer.classList.remove("dragging");
    localStorage.setItem(storageKey, grid.style.getPropertyValue(property));
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

// --- init ------------------------------------------------------------------

function init() {
  el("module-select").addEventListener("change", (e) => onModuleChange(e.target.value));
  el("lang-select").addEventListener("change", (e) => onLangChange(e.target.value));
  el("save-btn").addEventListener("click", doSave);
  el("compile-btn").addEventListener("click", doCompile);
  el("render-btn").addEventListener("click", doRender);

  const autocompile = el("autocompile");
  autocompile.checked = localStorage.getItem(AUTOCOMPILE_KEY) === "1";
  autocompile.addEventListener("change", () => {
    localStorage.setItem(AUTOCOMPILE_KEY, autocompile.checked ? "1" : "0");
    scheduleAutocompile();
  });

  wireResizer("row-resizer", "--context-height", CONTEXT_HEIGHT_KEY,
    (e, rect) => `${clamp(rect.bottom - e.clientY, 80, rect.height - 120)}px`);
  wireResizer("col-resizer", "--source-width", SOURCE_WIDTH_KEY,
    (e, rect) => `${clamp(e.clientX - rect.left, 200, rect.width - 200)}px`);

  wireCodeEditor("source-editor", "source-highlight", sourceMode, () => {
    if (!state.activeTarget) return;
    state.buffers[state.activeTarget] = el("source-editor").value;
    renderSourceTabs();
    scheduleAutocompile();
  });
  wireCodeEditor("meta-editor", "meta-highlight", "dgs-yaml", () => {
    state.meta = el("meta-editor").value;
    scheduleAutocompile();
  });

  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.addEventListener("click", () => switchOutputTab(t.dataset.output));
  });

  // Keep the scroll offset current so a reload lands where you were reading, not at the top.
  let scrollTimer = null;
  el("source-editor").addEventListener("scroll", () => {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(rememberScroll, 200);
  });

  // Nothing here auto-saves, so leaving with edits in the buffers would drop them silently.
  window.addEventListener("beforeunload", (e) => {
    rememberScroll();
    if (anyDirty()) e.preventDefault();
  });

  // Someone editing the address bar, or arriving from a bookmark in an open tab, should be
  // taken there. Ignore the hash we just wrote ourselves.
  window.addEventListener("hashchange", async () => {
    const wanted = readLocation();
    if (!wanted.unit) return;
    if (wanted.module === state.module?.name && wanted.unit === state.unit
        && wanted.lang === state.lang) {
      if (wanted.target && wanted.target !== state.activeTarget
          && state.targets.includes(wanted.target)) switchTarget(wanted.target);
      return;
    }
    if (!confirmDiscard()) return;
    try {
      await openUnit(wanted.module, wanted.unit, wanted.lang, wanted.target);
    } catch (e) {
      // A hand-edited or stale URL should say so, not fail silently in the console.
      setStatus(e.message, "error");
    }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      doCompile();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      doSave();
    }
  });
  loadModules();
}

init();
