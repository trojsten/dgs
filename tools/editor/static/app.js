const state = {
  problems: [],
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
  el("source-editor").value = state.buffers[target] ?? "";
  renderSourceTabs();
}

async function loadProblems() {
  state.problems = await fetchJSON("/api/problems");
  const sel = el("problem-select");
  sel.innerHTML = "";
  for (const p of state.problems) {
    const opt = document.createElement("option");
    opt.value = p.key;
    opt.textContent = p.key;
    sel.appendChild(opt);
  }
  if (state.problems.length) {
    await loadProblem(state.problems[0].key);
  }
}

async function loadProblem(key, lang) {
  if (anyDirty() && !confirm("Discard unsaved changes?")) {
    el("problem-select").value = state.key;
    return;
  }
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

  el("problem-select").value = key;
  const langSel = el("lang-select");
  langSel.innerHTML = "";
  for (const l of data.langs) {
    const opt = document.createElement("option");
    opt.value = l;
    opt.textContent = l;
    langSel.appendChild(opt);
  }
  langSel.value = data.lang;

  el("meta-editor").value = state.meta;
  el("preamble-editor").value = state.preamble;
  renderSourceTabs();
  switchTarget("problem");
  setStatus("Loaded", "ok");
  el("output-rendered").textContent = "";
  el("output-rendered").classList.remove("error");
}

async function doRender() {
  if (!state.key || !state.lang) return;
  state.buffers[state.activeTarget] = el("source-editor").value;
  state.meta = el("meta-editor").value;
  state.preamble = el("preamble-editor").value;

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
    if (body.ok) {
      out.textContent = body.rendered_md ?? "";
      out.classList.remove("error");
      setStatus("Rendered OK", "ok");
      state.baseline[state.activeTarget] = state.buffers[state.activeTarget];
      state.metaBaseline = state.meta;
      state.preambleBaseline = state.preamble;
      renderSourceTabs();
    } else {
      out.textContent = `$ make render/naboj/${state.key}/${state.lang}/${state.activeTarget}.md\n\n${body.stdout}\n${body.stderr}`;
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
  el("problem-select").addEventListener("change", (e) => loadProblem(e.target.value));
  el("lang-select").addEventListener("change", (e) => loadProblem(state.key, e.target.value));
  el("render-btn").addEventListener("click", doRender);
  el("source-editor").addEventListener("input", () => {
    state.buffers[state.activeTarget] = el("source-editor").value;
    renderSourceTabs();
  });
  el("meta-editor").addEventListener("input", () => {
    state.meta = el("meta-editor").value;
  });
  el("preamble-editor").addEventListener("input", () => {
    state.preamble = el("preamble-editor").value;
  });
  document.querySelectorAll("#pane-output .tab").forEach((t) => {
    t.addEventListener("click", () => switchOutputTab(t.dataset.output));
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      doRender();
    }
  });
  loadProblems();
}

init();
