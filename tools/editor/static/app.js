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
  caps: null,         // what this machine can do, from /api/capabilities
  hasPreview: false,
  hasTex: false,
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

/* Tab in a textarea moves focus, which is right for a form and wrong for an editor: every source
   here is indented, four spaces in Markdown and two in YAML, and there was no way to type it.
   Escape still blurs, so the keyboard is not trapped.

   This is the whole text transformation, kept pure so it can be reasoned about and tested without a
   DOM: given the value and the selection, what replaces what, and where the selection lands after.
   `from`/`to` is the span to overwrite. */
function indentEdit(value, selStart, selEnd, width, outdent) {
  // A bare caret inserts; anything selected indents the lines it touches. Tab never replaces a
  // selection here, unlike a general-purpose code editor: the text in this one is authored prose,
  // and a stray Tab that silently eats a selected sentence is a worse bargain than losing a
  // shortcut nobody needs.
  if (selStart === selEnd && !outdent) {
    // to the next tab stop rather than a fixed jump, so indentation stays in multiples of `width`
    const lineStart = value.lastIndexOf("\n", selStart - 1) + 1;
    const pad = width - ((selStart - lineStart) % width);
    return {from: selStart, to: selEnd, text: " ".repeat(pad),
            selStart: selStart + pad, selEnd: selStart + pad};
  }

  // whole lines: the block the selection touches, indented or outdented line by line
  const from = value.lastIndexOf("\n", selStart - 1) + 1;
  let to = value.indexOf("\n", selEnd);
  if (to === -1) to = value.length;

  const strip = new RegExp(`^ {1,${width}}`);
  let firstDelta = null, totalDelta = 0;
  const lines = value.slice(from, to).split("\n").map((line) => {
    let delta = 0;
    if (outdent) {
      const lead = line.match(strip);
      if (lead) {
        delta = -lead[0].length;
        line = line.slice(lead[0].length);
      }
    } else if (line.length) {
      // a blank line gains nothing: trailing whitespace on an empty line is what `encoding` flags
      delta = width;
      line = " ".repeat(width) + line;
    }
    if (firstDelta === null) firstDelta = delta;
    totalDelta += delta;
    return line;
  });

  return {
    from, to, text: lines.join("\n"),
    selStart: Math.max(from, selStart + firstDelta),
    selEnd: Math.max(from, selEnd + totalDelta),
  };
}

/* Apply an edit through `execCommand` where it exists: it is the only way to change a textarea and
   keep the browser's own undo stack, and it fires `input` so the highlight overlay follows. The
   fallback sets `value` directly and says so with an explicit event. */
function applyEdit(textarea, edit) {
  textarea.setSelectionRange(edit.from, edit.to);
  let ok = false;
  try {
    ok = document.execCommand("insertText", false, edit.text);
  } catch (e) {
    ok = false;
  }
  if (!ok) {
    const value = textarea.value;
    textarea.value = value.slice(0, edit.from) + edit.text + value.slice(edit.to);
    textarea.dispatchEvent(new Event("input", {bubbles: true}));
  }
  textarea.setSelectionRange(edit.selStart, edit.selEnd);
}

function wireIndent(textarea, width) {
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      textarea.blur();                       // the way out, since Tab no longer is
      return;
    }
    if (e.key !== "Tab" || e.ctrlKey || e.metaKey || e.altKey) return;
    e.preventDefault();
    applyEdit(textarea, indentEdit(textarea.value, textarea.selectionStart,
                                   textarea.selectionEnd, width, e.shiftKey));
  });
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

// --- the reference hover ---------------------------------------------------

/* What an author may type, fetched once. The same table `docs/filters.md` is generated from, so
   the tooltip and the document cannot disagree, and `core/tests/test_reference.py` holds both to
   the code they describe. */
async function loadReference() {
  try {
    state.reference = await fetchJSON("/api/reference");
  } catch {
    state.reference = null;      // the editor is still an editor without it
  }
}

/* The span under the pointer, or null.

   The overlay is `pointer-events: none` under a textarea that is not, which is the only way the
   two layers can work at all: the text you see is the overlay's and the text you edit is the
   textarea's. So `elementFromPoint` returns the textarea and never a token — unless the two are
   inverted for the duration of one hit test, which is what this does. Both styles are restored
   before the handler returns, so nothing observable changes.

   The alternative, walking every `[data-ref]` span and asking each for its rects, is O(tokens)
   forced layouts per mouse move; a solution with four hundred tags would make the pane crawl. */
function tokenAtPoint(editor, x, y) {
  const textarea = editor.querySelector(".code-input");
  const pre = editor.querySelector(".code-highlight");
  if (!textarea || !pre) return null;
  textarea.style.pointerEvents = "none";
  pre.style.pointerEvents = "auto";
  const hit = document.elementFromPoint(x, y);
  textarea.style.pointerEvents = "";
  pre.style.pointerEvents = "";
  return hit && pre.contains(hit) ? hit.closest("[data-ref]") : null;
}

/* The same question asked of the caret rather than the pointer, for F1.

   This one needs no DOM at all: `collectReferences` is the tokeniser's own, so the keyboard and
   the mouse are answering out of one definition of where a name is rather than two. */
function refAtCaret(textarea, lang) {
  const at = textarea.selectionStart;
  for (const found of collectReferences(textarea.value, lang)) {
    if (at >= found.start && at <= found.end) return found.ref;
  }
  return null;
}

function hoverElement() {
  let box = el("reference-hover");
  if (!box) {
    box = document.createElement("div");
    box.id = "reference-hover";
    box.hidden = true;
    document.body.appendChild(box);
  }
  return box;
}

function hideReference() {
  hoverElement().hidden = true;
}

const KIND_LABELS = {
  "filter": "filter", "global": "global", "attribute": "attribute", "operator": "operator",
  "namespace": "namespace", "meta-key": "meta.yaml key", "values-key": "values: key",
  "jinja-builtin": "Jinja's own",
};

/* `x`/`y` are where to anchor it, in viewport coordinates. Returns whether there was anything to
   show: a name the table does not hold is a miss, and a miss shows nothing rather than an empty
   box -- `eq.kin` names an equation this problem happens to have, and there is no entry for that
   and should not be. */
function showReference(ref, x, y) {
  const entry = state.reference?.entries?.[ref];
  if (!entry) { hideReference(); return false; }

  const box = hoverElement();
  const parts = [
    `<div><span class="ref-name">${escapeForHtml(entry.display)}</span>` +
    `<span class="ref-kind">${escapeForHtml(KIND_LABELS[entry.kind] || entry.kind)}` +
    `${entry.env === "static" ? " · .jtex only" : ""}</span></div>`,
  ];
  if (entry.signature && entry.signature !== entry.display) {
    parts.push(`<div class="ref-signature">${escapeForHtml(entry.signature)}</div>`);
  }
  parts.push(`<div class="ref-summary">${markdownish(entry.summary)}</div>`);
  if (entry.example) {
    parts.push(`<div class="ref-example"><b>${escapeForHtml(entry.example)}</b>` +
               `${escapeForHtml(entry.expect)}</div>`);
  }
  if (entry.note) parts.push(`<div class="ref-more">${markdownish(entry.note)}</div>`);
  box.innerHTML = parts.join("");
  box.hidden = false;

  // Placed below and right of the pointer, and flipped wherever that would run off the window --
  // a token near the bottom of a long file is exactly where this matters.
  const rect = box.getBoundingClientRect();
  const left = Math.max(4, Math.min(x + 14, window.innerWidth - rect.width - 8));
  const below = y + 18;
  const top = below + rect.height > window.innerHeight - 8
    ? Math.max(4, y - rect.height - 12)
    : below;
  box.style.left = `${left}px`;
  box.style.top = `${top}px`;
  return true;
}

function escapeForHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* The summaries are written in the same register as the rest of the documentation, which means
   they carry `code` and **emphasis**. Rendering those two and nothing else is enough to read
   them, and keeps the tooltip from needing a Markdown library for three characters of markup. */
function markdownish(s) {
  return escapeForHtml(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
}

/* One listener per pane, throttled to a frame: a mouse move fires far more often than the
   pointer actually crosses a token, and the hit test forces a layout. */
function wireReferenceHover(textareaId, lang) {
  const textarea = el(textareaId);
  const editor = textarea && textarea.closest(".code-editor");
  if (!editor) return;
  let pending = false;
  let shown = null;

  editor.addEventListener("mousemove", (e) => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      const span = tokenAtPoint(editor, e.clientX, e.clientY);
      const ref = span ? span.dataset.ref : null;
      if (!ref) { shown = null; hideReference(); return; }
      // Re-place it on every move even when the token has not changed, so it follows the pointer
      // along a long token instead of sitting where the pointer first entered.
      shown = ref;
      if (!showReference(ref, e.clientX, e.clientY)) shown = null;
    });
  });

  editor.addEventListener("mouseleave", () => { shown = null; hideReference(); });

  // The keyboard half. A hover is no use to someone mid-line with both hands on the keys, and
  // F1 is where help lives.
  textarea.addEventListener("keydown", (e) => {
    if (e.key !== "F1") {
      if (shown !== null) { shown = null; hideReference(); }
      return;
    }
    e.preventDefault();
    const mode = typeof lang === "function" ? lang() : lang;
    const ref = refAtCaret(textarea, mode);
    if (!ref) { setStatus("Nothing to look up at the caret", ""); return; }
    const where = textarea.getBoundingClientRect();
    if (!showReference(ref, where.left + 16, where.top + 16)) {
      setStatus(`No reference entry for ${ref}`, "");
    }
  });
  textarea.addEventListener("blur", hideReference);
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

/**
 * What this machine can do, fetched once at startup.
 *
 * Kept beside the per-unit facts (`hasPreview`, `hasTex`) because a tab is unavailable for
 * either reason and the user should not have to care which: `tierState` folds the two together
 * so every tab greys for the same reasons in the same way.
 */
async function loadCapabilities({ refresh = false } = {}) {
  try {
    state.caps = await fetchJSON(`/api/capabilities${refresh ? "?refresh=1" : ""}`);
  } catch {
    state.caps = null;            // never let a probe failure stop the editor from opening
  }
}

function tierFor(id) {
  return (state.caps?.tiers ?? []).find((t) => t.id === id) ?? null;
}

/** Why this output tab cannot be used, or null when it can. */
function tierState(output) {
  const tab = document.querySelector(`#pane-output .tab[data-output="${output}"]`);
  const tier = tierFor(tab?.dataset.tier);
  if (tier && !tier.ok) {
    return { reason: tier.reason, install: tier.install ?? [], label: tier.label };
  }
  if (output === "pdf" && state.unit && !state.hasPreview) {
    return { reason: `${state.module?.label ?? "This module"} declares no preview document`,
             install: [], label: "PDF" };
  }
  if (output === "tex" && state.unit && !state.hasTex) {
    return { reason: "this module declares no TeX rule", install: [], label: "TeX" };
  }
  if ((output === "tex" || output === "html" || output === "lint") && isAux(state.activeTarget)) {
    return { reason: `${state.activeTarget} is a figure, not prose`, install: [],
             label: output === "html" ? "HTML" : "TeX" };
  }
  return null;
}

function showUnavailable(output, blocked) {
  const panel = el("output-unavailable");
  panel.innerHTML = "";
  const title = document.createElement("p");
  title.className = "unavailable-title";
  title.textContent = `${blocked.label} is not available here.`;
  panel.appendChild(title);

  const why = document.createElement("p");
  why.textContent = blocked.reason;
  panel.appendChild(why);

  if (blocked.install.length) {
    const how = document.createElement("pre");
    how.textContent = blocked.install.join("\n");
    panel.appendChild(how);
    const doc = document.createElement("p");
    doc.className = "muted";
    doc.textContent = "See install.md, or run: uv run python tools/editor/capabilities.py";
    panel.appendChild(doc);

    const again = document.createElement("button");
    again.textContent = "Re-check";
    again.addEventListener("click", async () => {
      again.disabled = true;
      await loadCapabilities({ refresh: true });
      applyCapabilities();
      switchOutputTab(output);
    });
    panel.appendChild(again);
  }
}

/** Grey every tab whose tier is unavailable, and the actions that depend on one. */
function applyCapabilities() {
  document.querySelectorAll("#pane-output .tab[data-output]").forEach((tab) => {
    const blocked = tierState(tab.dataset.output);
    tab.classList.toggle("unavailable", Boolean(blocked));
    if (blocked) {
      tab.setAttribute("aria-disabled", "true");
      tab.title = blocked.reason;
    } else {
      tab.removeAttribute("aria-disabled");
      tab.title = "";
    }
  });
  const pdf = tierState("pdf");
  el("compile-btn").disabled = Boolean(pdf);
  el("compile-btn").title = pdf ? pdf.reason : "";
  el("autocompile").disabled = Boolean(pdf);
}

function syncActionsForTarget() {
  const aux = isAux(state.activeTarget);
  el("render-btn").disabled = aux && !state.activeTarget.endsWith(".gp");
  // The Lint and TeX tabs used to be `disabled` here. They are greyed by applyCapabilities
  // instead, so the pane behind them can say *why* -- a disabled button has nowhere to.
  applyCapabilities();
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
  // Stay on the same file. Comparing a translation means flipping between languages on *one*
  // of them, and being thrown back to `problem` every time made that unusable. `openUnit`
  // falls back to the first target when the new language does not have this one.
  await openUnit(state.module.name, state.unit, lang, state.activeTarget);
}

/**
 * Why there is nothing to edit.
 *
 * `load_modules` skips a module whose `source/<name>/` is missing, which on a fresh clone means
 * every one of them -- and the editor would otherwise open showing an empty picker and no hint.
 * `source/` cannot be populated by `git submodule update --init` here, so the panel names the
 * repositories and the paths they belong at.
 */
function renderEmptySource() {
  const source = state.caps?.source;
  const host = el("empty-source");
  if (!host) return;
  host.hidden = false;
  host.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "No sources checked out";
  host.appendChild(title);

  const lead = document.createElement("p");
  lead.textContent = "The editor found no module with a populated source/ directory.";
  host.appendChild(lead);

  for (const module of source?.modules ?? []) {
    if (module.units) continue;
    const head = document.createElement("p");
    head.innerHTML = `<strong>${module.label}</strong> &mdash; ` +
      (module.present ? "source/ directory exists but holds no units" : "not checked out");
    host.appendChild(head);
    if (module.expected?.length) {
      const how = document.createElement("pre");
      how.textContent = module.expected
        .map((e) => `git clone ${e.url} ${e.path}`).join("\n");
      host.appendChild(how);
    }
  }
  if (source?.note) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = source.note;
    host.appendChild(note);
  }
}

async function loadModules() {
  state.modules = await fetchJSON("/api/modules");
  if (!state.modules.length) { renderEmptySource(); return; }
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
  state.hasTex = data.has_tex;
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

let pdfView = null;
let pdfViewLoading = null;

/**
 * The pdf.js viewer, loaded on first use: it is an ES module and this file is not, and a
 * `<script type="module">` would run after `init()` had already asked for a PDF. The promise is
 * kept so that two early calls share one viewer rather than wiring the buttons twice.
 */
function pdfViewer() {
  pdfViewLoading ??= import("/static/pdfview.js").then(({ PdfView }) => {
    pdfView = new PdfView(el("pdf-view"), el("pdf-zoom-label"));
    el("pdf-zoom-in").addEventListener("click", () => pdfView.zoomBy(1.2));
    el("pdf-zoom-out").addEventListener("click", () => pdfView.zoomBy(1 / 1.2));
    el("pdf-zoom-fit").addEventListener("click", () => pdfView.setZoom("fit"));
    return pdfView;
  });
  return pdfViewLoading;
}

/**
 * Point the preview at `url`, or clear it when `url` is null.
 *
 * The viewer keeps its zoom and scroll offset across a load, so a recompile lands on the spot
 * being read and a language switch on the same spot in the translation.
 */
async function showPdf(url, { stale = false } = {}) {
  const view = el("pdf-view");
  const placeholder = el("pdf-placeholder");
  const wrapper = el("output-pdf");
  const link = el("pdf-newtab");
  const zoom = el("pdf-zoom");

  wrapper.classList.toggle("stale", stale);

  if (!url) {
    state.pdfUrl = null;
    view.classList.remove("loaded");
    zoom.hidden = true;
    pdfView?.clear();
    placeholder.hidden = false;
    placeholder.textContent = "Nothing compiled yet — press Ctrl/Cmd+Enter.";
    link.removeAttribute("href");
    return;
  }

  const sameDocument = state.pdfUrl === url;
  state.pdfUrl = url;
  link.href = url;

  // A failed compile did not rewrite the cached file, so there is nothing to refetch.
  if (stale && sameDocument) return;

  try {
    await (await pdfViewer()).load(url);
    placeholder.hidden = true;
    view.classList.add("loaded");
    zoom.hidden = false;
  } catch (e) {
    view.classList.remove("loaded");
    zoom.hidden = true;
    placeholder.hidden = false;
    placeholder.textContent = `Cannot show the PDF: ${e.message}`;
  }
}

function switchOutputTab(name) {
  state.activeOutput = name;
  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.output === name);
  });
  const blocked = tierState(name);
  el("output-pdf").hidden = name !== "pdf" || Boolean(blocked);
  el("output-rendered").hidden = name !== "rendered" || Boolean(blocked);
  el("output-tex").hidden = name !== "tex" || Boolean(blocked);
  el("output-html").hidden = name !== "html" || Boolean(blocked);
  el("output-lint").hidden = name !== "lint" || Boolean(blocked);
  el("output-log").hidden = name !== "log";
  el("output-unavailable").hidden = !blocked || name === "log";
  if (blocked) {
    showUnavailable(name, blocked);
    return;                       // no point asking the server for something it cannot do
  }
  if (name === "lint") doLint();
}

// --- actions ---------------------------------------------------------------

/**
 * The preview itself ignores the fragment; it is for "open in tab", which is the browser's viewer.
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

/* The fragment the web gets, shown as a page rather than as markup.
 *
 * `srcdoc` with an absolute `<base>` under `/api/output/`, so the relative pictures resolve
 * exactly as they would on the web -- one that does not load here would not load there either,
 * and the pane should show that rather than hide it.
 *
 * MathJax typesets it, with `static/mathjax-dgs.js` ahead of it supplying the siunitx macros
 * MathJax has none of. `allow-scripts` is therefore required, and is given *without*
 * `allow-same-origin`: the frame runs on an opaque origin and cannot reach back into the editor. */
async function doHtml() {
  if (!state.unit || !state.activeTarget) return;
  if (tierState("html")) { switchOutputTab("html"); return; }
  setStatus("Converting…", "dirty");
  try {
    const body = await post("/api/html", { target: state.activeTarget });
    setLog(logOf(body));
    markSaved();

    const frame = el("html-view");
    switchOutputTab("html");
    if (body.ok) {
      // Absolute, because a `srcdoc` document has no URL of its own for a relative one to
      // resolve against.
      const base = `${location.origin}/api/output/` +
        (body.html_target ?? "").replace(/^output\//, "").replace(/[^/]*$/, "");
      frame.srcdoc =
        `<!doctype html><html><head><meta charset="utf-8">` +
        `<base href="${base}">` +
        `<script src="${location.origin}/static/mathjax-dgs.js"><\/script>` +
        `<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"><\/script>` +
        `<style>body{font:16px/1.5 system-ui,sans-serif;margin:1.25rem;color:#111}` +
        `img{max-width:100%}</style></head><body>${body.html ?? ""}</body></html>`;
      setStatus("HTML OK", "ok");
    } else {
      frame.srcdoc =
        `<!doctype html><html><head><meta charset="utf-8">` +
        `<style>body{font:13px/1.5 ui-monospace,monospace;margin:1rem;color:#a00;white-space:pre-wrap}` +
        `</style></head><body></body></html>`;
      frame.srcdoc = frame.srcdoc.replace("</body>", escapeForHtml(logOf(body)) + "</body>");
      setStatus(failureStatus(body, "convert"), "error");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function doTex() {
  if (!state.unit || !state.activeTarget) return;
  if (tierState("tex")) { switchOutputTab("tex"); return; }
  setStatus("Converting…", "dirty");
  try {
    const body = await post("/api/tex", { target: state.activeTarget });
    setLog(logOf(body));
    markSaved();

    const out = el("output-tex");
    const code = el("output-tex-code");
    switchOutputTab("tex");
    if (body.ok) {
      code.innerHTML = highlight(body.tex ?? "", "dgs-tex");
      out.classList.remove("error");
      setStatus("TeX OK", "ok");
    } else {
      code.textContent = logOf(body);
      out.classList.add("error");
      setStatus(failureStatus(body, "convert"), "error");
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

  wireIndent(el("source-editor"), 4);      // display blocks indent by four
  wireIndent(el("meta-editor"), 2);        // YAML by two
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

  // Both panes, because the vocabulary is written in both -- and `derived:` in the meta is where
  // `PQ`, `QL` and `.to()` actually live: 158 of the 160 `PQ` in the repository are there.
  wireReferenceHover("source-editor", sourceMode);
  wireReferenceHover("meta-editor", "dgs-yaml");

  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.addEventListener("click", () => {
      // TeX is built on demand like the PDF, not fetched like a file already on disk.
      if (t.dataset.output === "tex" && !tierState("tex")) doTex();
      else if (t.dataset.output === "html" && !tierState("html")) doHtml();
      else switchOutputTab(t.dataset.output);
    });
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
  loadCapabilities().then(() => {
    applyCapabilities();
    loadModules();
  });
  loadReference();        // independent of everything else, and nothing waits on it
}

init();
