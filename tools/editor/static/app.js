const state = {
  problems: [],
  problemIndex: {},   // comp -> vol -> [{pid, key, langs, optional_targets}]
  comp: null,
  vol: null,
  key: null,
  lang: null,
  activeTarget: "problem",
  buffers: {},        // target -> current text
  baseline: {},        // target -> last-saved text (for dirty tracking)
  meta: "",
  metaBaseline: "",
  preamble: "",
  preambleBaseline: "",
  optionalTargets: [],
  activeOutput: "rendered",
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

function sourceTargets() {
  return ["problem", "solution", ...state.optionalTargets];
}

function isDirty(target) {
  return (state.buffers[target] ?? "") !== (state.baseline[target] ?? "");
}

function anyDirty() {
  if (state.meta !== state.metaBaseline) return true;
  if (state.preamble !== state.preambleBaseline) return true;
  return sourceTargets().some(isDirty);
}

// --- syntax highlighting overlay -------------------------------------------

function refreshHighlight(textareaId, highlightId, lang) {
  const text = el(textareaId).value;
  el(highlightId).innerHTML = highlight(text + "\n", lang);
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

function renderSourceTabs() {
  const bar = el("source-tabs");
  bar.innerHTML = "";
  for (const target of sourceTargets()) {
    const btn = document.createElement("button");
    btn.className = "tab" + (target === state.activeTarget ? " active" : "");
    if (isDirty(target)) btn.classList.add("dirty");
    btn.textContent = labelFor(target);
    btn.dataset.target = target;
    btn.addEventListener("click", () => switchTarget(target));
    bar.appendChild(btn);
  }
}

function labelFor(target) {
  return {
    "problem": "Problem",
    "solution": "Solution",
    "answer": "Answer",
    "answer-also": "Answer also",
    "answer-interval": "Answer interval",
  }[target] || target;
}

function switchTarget(target) {
  state.activeTarget = target;
  setEditorValue("source-editor", "source-highlight", "dgs-md", state.buffers[target] ?? "");
  renderSourceTabs();
}

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
  fillSelect(el("pid-select"), problems.map((p) => p.pid), (pid) => pid);
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
    state.problemIndex[comp][vol].push({ pid, key: p.key, langs: p.langs, optional_targets: p.optional_targets });
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
  const meta = state.problems.find((p) => p.key === key);

  state.key = key;
  state.lang = data.lang;
  state.optionalTargets = meta ? meta.optional_targets : [];
  state.activeTarget = "problem";

  state.meta = data.meta_yaml ?? "";
  state.metaBaseline = state.meta;
  state.preamble = data.preamble_md ?? "";
  state.preambleBaseline = state.preamble;

  state.buffers = {
    problem: data.problem_md ?? "",
    solution: data.solution_md ?? "",
    answer: data.answer_md ?? "",
    "answer-also": data.answer_also_md ?? "",
    "answer-interval": data.answer_interval_md ?? "",
  };
  state.baseline = { ...state.buffers };

  const [comp, vol, , pid] = key.split("/");
  el("comp-select").value = comp;
  el("vol-select").value = vol;
  el("pid-select").value = pid;

  const langSel = el("lang-select");
  langSel.innerHTML = "";
  for (const l of data.langs) {
    const opt = document.createElement("option");
    opt.value = l;
    opt.textContent = l;
    langSel.appendChild(opt);
  }
  langSel.value = data.lang;

  setEditorValue("meta-editor", "meta-highlight", "dgs-yaml", state.meta);
  setEditorValue("preamble-editor", "preamble-highlight", "dgs-preamble", state.preamble);
  renderSourceTabs();
  switchTarget("problem");
  setStatus("Loaded", "ok");
  el("output-rendered-code").innerHTML = "";
  el("output-rendered").classList.remove("error");
}

function captureEditors() {
  state.buffers[state.activeTarget] = el("source-editor").value;
  state.meta = el("meta-editor").value;
  state.preamble = el("preamble-editor").value;
}

function markSaved() {
  state.baseline[state.activeTarget] = state.buffers[state.activeTarget];
  state.metaBaseline = state.meta;
  state.preambleBaseline = state.preamble;
  renderSourceTabs();
}

async function doSave() {
  if (!state.key || !state.lang) return;
  captureEditors();
  setStatus("Saving…", "dirty");
  try {
    const body = await fetchJSON("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key: state.key,
        lang: state.lang,
        target: state.activeTarget,
        files: {
          meta_yaml: state.meta,
          preamble_md: state.preamble,
          content: state.buffers[state.activeTarget],
        },
      }),
    });
    if (body.ok) {
      markSaved();
      setStatus("Saved", "ok");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function doRender() {
  if (!state.key || !state.lang) return;
  captureEditors();

  setStatus("Rendering…", "dirty");
  try {
    const body = await fetchJSON("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key: state.key,
        lang: state.lang,
        target: state.activeTarget,
        files: {
          meta_yaml: state.meta,
          preamble_md: state.preamble,
          content: state.buffers[state.activeTarget],
        },
      }),
    });

    const out = el("output-rendered");
    const code = el("output-rendered-code");
    if (body.ok) {
      code.innerHTML = highlight(body.rendered_md ?? "", "dgs-md");
      out.classList.remove("error");
      setStatus("Rendered OK", "ok");
      markSaved();
    } else {
      const dump = `$ make render/naboj/${state.key}/${state.lang}/${state.activeTarget}.md\n\n${body.stdout}\n${body.stderr}`;
      code.innerHTML = escapeHtml(dump);
      out.classList.add("error");
      setStatus(`Render failed (exit ${body.returncode})`, "error");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function doLint() {
  if (!state.key || !state.lang) return;
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

const CONTEXT_HEIGHT_KEY = "dgs-editor-context-height";

function wireRowResizer() {
  const resizer = el("row-resizer");
  const grid = el("grid");
  let dragging = false;

  const saved = localStorage.getItem(CONTEXT_HEIGHT_KEY);
  if (saved) grid.style.setProperty("--context-height", saved);

  resizer.addEventListener("mousedown", (e) => {
    dragging = true;
    resizer.classList.add("dragging");
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const gridRect = grid.getBoundingClientRect();
    const height = Math.min(
      Math.max(gridRect.bottom - e.clientY, 80),
      gridRect.height - 120
    );
    grid.style.setProperty("--context-height", `${height}px`);
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    resizer.classList.remove("dragging");
    localStorage.setItem(CONTEXT_HEIGHT_KEY, grid.style.getPropertyValue("--context-height"));
  });
}

function switchOutputTab(name) {
  state.activeOutput = name;
  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.output === name);
  });
  el("output-rendered").hidden = name !== "rendered";
  el("output-lint").hidden = name !== "lint";
  if (name === "lint") doLint();
}

function init() {
  el("comp-select").addEventListener("change", (e) => onCompChange(e.target.value));
  el("vol-select").addEventListener("change", (e) => onVolChange(e.target.value));
  el("pid-select").addEventListener("change", (e) => onPidChange(e.target.value));
  el("lang-select").addEventListener("change", (e) => onLangChange(e.target.value));
  el("save-btn").addEventListener("click", doSave);
  el("render-btn").addEventListener("click", doRender);
  wireRowResizer();

  wireCodeEditor("source-editor", "source-highlight", "dgs-md", () => {
    state.buffers[state.activeTarget] = el("source-editor").value;
    renderSourceTabs();
  });
  wireCodeEditor("meta-editor", "meta-highlight", "dgs-yaml", () => {
    state.meta = el("meta-editor").value;
  });
  wireCodeEditor("preamble-editor", "preamble-highlight", "dgs-preamble", () => {
    state.preamble = el("preamble-editor").value;
  });

  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.addEventListener("click", () => switchOutputTab(t.dataset.output));
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      doRender();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      doSave();
    }
  });
  loadProblems();
}

init();
