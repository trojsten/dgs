const state = {
  problems: [],
  problemIndex: {},   // comp -> vol -> [{pid, key, langs}]
  comp: null,
  vol: null,
  key: null,
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
  if (state.activeTarget) state.buffers[state.activeTarget] = el("source-editor").value;
  state.activeTarget = target;
  setEditorValue("source-editor", "source-highlight", sourceMode, state.buffers[target] ?? "");
  renderSourceTabs();
  syncActionsForTarget();
}

// --- problem picker --------------------------------------------------------

function fillSelect(selectEl, values, labelFn) {
  selectEl.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = labelFn ? labelFn(v) : v;
    selectEl.appendChild(opt);
  }
}

function pidsFor(comp, vol) {
  return (state.problemIndex[comp]?.[vol]) ?? [];
}

function populateVolumes(comp, preferredVol) {
  const vols = Object.keys(state.problemIndex[comp] ?? {}).sort();
  fillSelect(el("vol-select"), vols);
  state.vol = vols.includes(preferredVol) ? preferredVol : vols[0];
  el("vol-select").value = state.vol;
}

function populateProblems(comp, vol, preferredPid) {
  const problems = pidsFor(comp, vol);
  // Mark the problems that have no meta.yaml yet, rather than leaving you to work out why
  // a compile fails: nearly half of chem is still unconverted.
  const marks = Object.fromEntries(problems.map((p) => [p.pid, p.hasMeta ? "" : " \u26a0"]));
  fillSelect(el("pid-select"), problems.map((p) => p.pid), (pid) => pid + (marks[pid] ?? ""));
  const match = problems.find((p) => p.pid === preferredPid) ?? problems[0];
  el("pid-select").value = match ? match.pid : "";
  return match ? match.key : null;
}

async function loadProblems() {
  state.problems = await fetchJSON("/api/problems");
  state.problemIndex = {};
  for (const p of state.problems) {
    const [comp, vol, , pid] = p.key.split("/");
    (state.problemIndex[comp] ??= {})[vol] ??= [];
    state.problemIndex[comp][vol].push({ pid, key: p.key, langs: p.langs, hasMeta: p.has_meta });
  }
  for (const comp in state.problemIndex) {
    for (const vol in state.problemIndex[comp]) {
      state.problemIndex[comp][vol].sort((a, b) => a.pid.localeCompare(b.pid));
    }
  }

  const comps = Object.keys(state.problemIndex).sort();
  fillSelect(el("comp-select"), comps);
  if (!comps.length) return;

  state.comp = comps[0];
  populateVolumes(state.comp);
  const key = populateProblems(state.comp, state.vol);
  if (key) await loadProblem(key);
}

function confirmDiscard(revertEl, revertValue) {
  if (anyDirty() && !confirm("Discard unsaved changes?")) {
    revertEl.value = revertValue;
    return false;
  }
  return true;
}

async function onCompChange(comp) {
  if (!confirmDiscard(el("comp-select"), state.comp)) return;
  state.comp = comp;
  populateVolumes(comp);
  const key = populateProblems(comp, state.vol);
  if (key) await loadProblem(key);
}

async function onVolChange(vol) {
  if (!confirmDiscard(el("vol-select"), state.vol)) return;
  state.vol = vol;
  const key = populateProblems(state.comp, vol);
  if (key) await loadProblem(key);
}

async function onPidChange(pid) {
  const current = pidsFor(state.comp, state.vol).find((p) => p.key === state.key);
  if (!confirmDiscard(el("pid-select"), current ? current.pid : pid)) return;
  const match = pidsFor(state.comp, state.vol).find((p) => p.pid === pid);
  if (match) await loadProblem(match.key);
}

async function onLangChange(lang) {
  if (!confirmDiscard(el("lang-select"), state.lang)) return;
  await loadProblem(state.key, lang);
}

async function loadProblem(key, lang) {
  const url = lang ? `/api/problem/${key}?lang=${lang}` : `/api/problem/${key}`;
  const data = await fetchJSON(url);

  state.key = key;
  state.lang = data.lang;
  state.targets = data.targets;
  state.activeTarget = null;

  state.meta = data.meta_yaml ?? "";
  state.metaBaseline = state.meta;

  state.buffers = {};
  for (const target of state.targets) state.buffers[target] = data.files[target] ?? "";
  state.baseline = { ...state.buffers };

  const [comp, vol, , pid] = key.split("/");
  el("comp-select").value = comp;
  el("vol-select").value = vol;
  el("pid-select").value = pid;
  fillSelect(el("lang-select"), data.langs);
  el("lang-select").value = data.lang;

  setEditorValue("meta-editor", "meta-highlight", "dgs-yaml", state.meta);
  el("meta-label").textContent = data.meta_yaml === null ? "meta.yaml (does not exist yet)" : "meta.yaml";
  switchTarget(state.targets[0] ?? null);
  setStatus("Loaded", "ok");

  el("output-rendered-code").innerHTML = "";
  el("output-rendered").classList.remove("error");
  setLog("");
  showPdf(null);
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
    body: JSON.stringify({ key: state.key, lang: state.lang, files: dirtyFiles(), ...extra }),
  });
}

async function doSave() {
  if (!state.key || !state.lang) return;
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
function pdfUrlFor(key, lang) {
  return `/api/pdf/${key}/${lang}#pagemode=none`;
}

async function doCompile() {
  if (!state.key || !state.lang) return;
  setStatus("Compiling…", "dirty");
  try {
    const body = await post("/api/compile");
    setLog(logOf(body));
    markSaved();

    if (body.ok) {
      showPdf(pdfUrlFor(state.key, state.lang));
      switchOutputTab("pdf");
      setStatus("Compiled", "ok");
    } else {
      // Keep the last good render on screen, badged as out of date, and show why.
      if (body.has_pdf) showPdf(state.pdfUrl ?? pdfUrlFor(state.key, state.lang), { stale: true });
      switchOutputTab("log");
      setStatus(failureStatus(body, "compile"), "error");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function doRender() {
  if (!state.key || !state.lang || !state.activeTarget) return;
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
  if (!state.key || !state.lang || !state.activeTarget) return;
  const box = el("output-lint");
  box.textContent = "Linting…";
  try {
    const body = await fetchJSON("/api/lint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: state.key, lang: state.lang, target: state.activeTarget }),
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
  el("comp-select").addEventListener("change", (e) => onCompChange(e.target.value));
  el("vol-select").addEventListener("change", (e) => onVolChange(e.target.value));
  el("pid-select").addEventListener("change", (e) => onPidChange(e.target.value));
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
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      doCompile();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      doSave();
    }
  });
  loadProblems();
}

init();
