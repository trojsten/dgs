import argparse
import re
import shutil
import subprocess
import threading
from pathlib import Path

from flask import Flask, jsonify, request, render_template, send_file

# `descriptors`, not `modules`: the repo root holds a `modules/` namespace package, and whichever
# came first on sys.path would win.
from descriptors import (AUX_EXTENSIONS, RENDERABLE_AUX_EXTENSIONS,
                         discover_units, load_modules)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Last known-good preview PDFs. `double_xelatex` runs with `-halt-on-error`, so a failed compile
# can leave a truncated file in `output/`; serving a copy means a broken edit keeps showing the
# previous render beside the error log instead of a blank pane.
PDF_CACHE = REPO_ROOT / "build" / ".editor-preview"

# Stands in for the language in cache paths for modules that do not have one.
NO_LANGUAGE = "_"

LANG_RE = re.compile(r"^[a-z]{2,3}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b[()][A-Za-z0-9]")

BUILD_LOCK = threading.Lock()

MODULES = load_modules(REPO_ROOT)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


class BadRequest(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({"error": e.message}), 400


# --- resolving what the request is talking about ----------------------------

class Unit:
    """
    One editable thing, resolved and validated: which module, which directory, what it may hold.

    The unit path is checked by *membership* in the module's discovered set rather than by
    inspecting the string, which settles path traversal at the same time -- no glob ever yields
    a path outside the module's source root.
    """
    def __init__(self, module_name, unit, lang=None):
        self.module = MODULES.get(module_name)
        if self.module is None:
            raise BadRequest(f"Unknown module: {module_name!r}")

        self.kind = discover_units(self.module).get(unit)
        if self.kind is None:
            raise BadRequest(f"No such {self.module.label} unit: {unit!r}")

        self.name = unit
        self.path = self.module.root / unit
        self.languages = self.available_languages()
        self.lang = self.resolve_language(lang)

    def available_languages(self):
        if not self.module.languages:
            return []
        return sorted(
            child.name for child in self.path.iterdir()
            if child.is_dir() and any((child / f"{t}.md").is_file() for t in self.kind.translated)
        )

    def resolve_language(self, lang):
        if not self.module.languages:
            return None
        if lang is None:
            return self.languages[0] if self.languages else None
        if not LANG_RE.match(lang) or lang not in self.languages:
            raise BadRequest(f"Invalid or unavailable language: {lang!r}")
        return lang

    # -- files ---------------------------------------------------------------

    def is_aux(self, target):
        """An auxiliary file is named by path and extension; declared targets are bare names."""
        return target not in self.kind.targets

    def aux_path(self, target):
        """
        Resolve an auxiliary target. Unlike a declared target this is arbitrary text, so it is
        checked rather than trusted: inside the unit, and of an editable kind.
        """
        if not target or target.startswith("/") or ".." in target.split("/"):
            raise BadRequest(f"Invalid file: {target!r}")
        path = (self.path / target).resolve()
        if not path.is_relative_to(self.path.resolve()) or path.suffix not in AUX_EXTENSIONS:
            raise BadRequest(f"Not an editable auxiliary file: {target!r}")
        return path

    def source_path(self, target):
        if self.is_aux(target):
            return self.aux_path(target)
        if self.kind.is_translated(target):
            if not self.lang:
                raise BadRequest(f"{target} is translated, but no language is selected.")
            return self.path / self.lang / f"{target}.md"
        return self.path / f"{target}.md"

    def aux_files(self):
        """
        Every `.gp` and `.dat` the unit holds, at its own level and inside the language directory,
        named relative to the unit so `sk/data.dat` stays distinct from `data.dat`.
        """
        found = []
        directories = [self.path] + ([self.path / self.lang] if self.lang else [])
        for directory in directories:
            if directory.is_dir():
                found += sorted(
                    path.relative_to(self.path).as_posix()
                    for path in directory.iterdir()
                    if path.is_file() and path.suffix in AUX_EXTENSIONS
                )
        return found

    def existing_targets(self):
        """Every file the unit actually has, declared ones in the order the descriptor lists."""
        declared = [t for t in self.kind.targets
                    if (self.lang or not self.kind.is_translated(t))
                    and self.source_path(t).is_file()]
        return declared + self.aux_files()

    @property
    def meta_path(self):
        return self.path / "meta.yaml"

    # -- make targets --------------------------------------------------------

    def _format(self, template):
        parent = self.name.rsplit("/", 1)[0] if "/" in self.name else ""
        return template.format(unit=self.name, parent=parent,
                               language=self.lang or "", target="{target}")

    def render_target(self, target):
        """
        The make target that renders this file. A gnuplot script keeps its own name and extension
        (`render/<module>/%.gp`); a declared target is always `.md`.
        """
        if self.is_aux(target):
            return f"render/{self.module.name}/{self.name}/{target}"
        return self._format(self.kind.render).format(target=target)

    def render_path(self, target):
        return REPO_ROOT / self.render_target(target)

    def preview_target(self):
        if not self.kind.preview:
            return None
        return self._format(self.kind.preview)

    def cached_pdf(self):
        return PDF_CACHE / self.module.name / self.name / (self.lang or NO_LANGUAGE) / "preview.pdf"


def unit_from_body(body):
    return Unit(body.get("module"), body.get("unit"), body.get("lang"))


def read_if_exists(path):
    return path.read_text() if path.is_file() else None


# --- reading ----------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


def hidden_levels(module):
    """
    Path levels the picker should not offer, because the descriptor leaves no choice there.

    A level qualifies only if every unit kind pins it to a literal *and* they all pin it to the
    same one -- Náboj's `problems/`. Scholar also pins its third level, but to `handouts` in one
    kind and `homework` in another, so that one is a choice and stays. Neither is the same thing
    as a level that merely has one value today: seminar has repositories besides FKS, and hiding
    the competition because only FKS is checked out would give no hint that the others exist.
    """
    depths = {}
    for kind in module.kinds:
        segments = kind.glob.split("/")
        for depth, segment in enumerate(segments):
            literal = segment if depth in kind.fixed_levels else None
            depths.setdefault(depth, set()).add(literal)
    return sorted(depth for depth, values in depths.items()
                  if len(values) == 1 and None not in values)


@app.get("/api/modules")
def api_modules():
    """
    Everything the front end needs to build its picker and to read a URL: the modules that exist
    and every unit in each. Sent whole because the client resolves a hash by finding the longest
    unit path that prefixes it, units being of different depths in different modules.
    """
    return jsonify([
        {
            "name": module.name,
            "label": module.label,
            "languages": module.languages,
            "units": sorted(discover_units(module)),
            # What each path level is, and which of them are not a choice at all.
            "levels": sorted({(i, name)
                              for kind in module.kinds
                              for i, name in enumerate(kind.levels)}),
            "hidden_levels": hidden_levels(module),
        }
        for module in sorted(MODULES.values(), key=lambda m: m.label)
    ])


@app.get("/api/unit/<module>/<path:unit>")
def api_unit(module, unit):
    resolved = Unit(module, unit, request.args.get("lang"))
    targets = resolved.existing_targets()
    return jsonify({
        "module": module,
        "unit": unit,
        "langs": resolved.languages,
        "lang": resolved.lang,
        "targets": targets,
        "has_meta": resolved.meta_path.is_file(),
        # So a reload can put the last compiled page straight back in the pane instead of an
        # empty placeholder: the PDF outlives the browser session, it is in the cache.
        "has_pdf": resolved.cached_pdf().is_file(),
        "has_preview": resolved.preview_target() is not None,
        "meta_yaml": read_if_exists(resolved.meta_path),
        "files": {t: read_if_exists(resolved.source_path(t)) for t in targets},
    })


# --- running make -----------------------------------------------------------

def run_make(target, *, timeout=60):
    return subprocess.run(
        ["uv", "run", "make", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# XeLaTeX runs with `-file-line-error`, so its errors arrive as `file.tex:12: message`.
LATEX_ERROR_RE = re.compile(r"^\.?/?\S+\.tex:(\d+):\s*(.+)$", re.MULTILINE)
# The renderer raises through to the top level, so an authoring mistake in meta.yaml or in a
# `(§ … §)` tag reaches us as the last line of a Python traceback.
PYTHON_ERROR_RE = re.compile(r"^(?:[\w.]+\.)?(\w*(?:Error|Exception)):\s*(.+)$", re.MULTILINE)
# `MissingVariablesError` interpolates the whole template into its message before naming the
# variables, so the part worth reading is the list at the very end, several lines down. Greedy
# `.*` skips the template to the last `: [...]`.
MISSING_VARS_RE = re.compile(r"MissingVariablesError: Missing variables in .*: (\[[^\[\]]*\])", re.DOTALL)


def elide(summary, limit=160):
    summary = " ".join(summary.split())
    return summary if len(summary) <= limit else summary[:limit - 1].rstrip() + "…"


def summarise_failure(text):
    """
    The one line worth reading, pulled out of a few hundred that are not.

    A bad meta.yaml buries `Missing keys: 'authors', 'tags'` under a pretty-printed schema and a
    twenty-frame traceback; a bad equation buries the TeX error under the package banner. Both
    stay in the log, but neither should have to be hunted for.
    """
    if missing := MISSING_VARS_RE.search(text):
        return elide(f"Missing variables: {missing.group(1)}")
    if latex := LATEX_ERROR_RE.search(text):
        return elide(f"line {latex.group(1)}: {latex.group(2)}")
    if python := list(PYTHON_ERROR_RE.finditer(text)):
        name, message = python[-1].groups()
        return elide(f"{name}: {message}")
    return None


def make_result(target, result):
    combined = ANSI_RE.sub("", result.stdout + result.stderr)
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "command": f"make {target}",
        "summary": None if result.returncode == 0 else summarise_failure(combined),
        "stdout": ANSI_RE.sub("", result.stdout),
        "stderr": ANSI_RE.sub("", result.stderr),
    }


def refusal(target, summary, explanation):
    """A failure of ours rather than make's: no exit code, and a reason worth reading."""
    return {"ok": False, "returncode": None, "command": f"make {target}",
            "summary": summary, "stdout": explanation, "stderr": ""}


def missing_meta_result(target, unit):
    """
    Every render rule takes the unit's `meta.yaml` as a prerequisite, so without one make cannot
    build the chain at all and reports `No rule to make target`, naming the PDF rather than the
    file that is actually missing. Say what is wrong instead -- an unconverted unit opens in the
    editor precisely so that a meta.yaml can be written for it.
    """
    return refusal(
        target, "meta.yaml does not exist",
        f"{unit.meta_path.relative_to(REPO_ROOT)} does not exist.\n\n"
        f"Every render rule needs it, so nothing can be built until it is written. "
        f"Fill in the meta.yaml pane and save.\n",
    )


def build(unit, make_target, *, timeout=60):
    if not unit.meta_path.is_file():
        return missing_meta_result(make_target, unit)
    return make_result(make_target, run_make(make_target, timeout=timeout))


# --- writing ----------------------------------------------------------------

def write_files(unit, files):
    """
    Write back every buffer the editor sent. All of a unit's files are open at once, so a save or
    a compile has to flush all the dirty ones -- compiling only the active tab would silently
    preview a mixture of edited and stale text.
    """
    if files.get("meta_yaml") is not None:
        unit.meta_path.write_text(files["meta_yaml"])

    for target, content in (files.get("targets") or {}).items():
        source_path = unit.source_path(target)
        if not source_path.is_file():
            raise BadRequest(f"Refusing to create a new file: {target} does not exist")
        source_path.write_text(content)


@app.post("/api/save")
def api_save():
    body = request.get_json(force=True)
    unit = unit_from_body(body)
    with BUILD_LOCK:
        write_files(unit, body.get("files") or {})
    return jsonify({"ok": True})


@app.post("/api/render")
def api_render():
    body = request.get_json(force=True)
    unit = unit_from_body(body)
    target = body.get("target")
    unit.source_path(target)        # validates
    if unit.is_aux(target) and Path(target).suffix not in RENDERABLE_AUX_EXTENSIONS:
        raise BadRequest(f"{target} is copied verbatim, not rendered -- nothing to preview.")

    with BUILD_LOCK:
        write_files(unit, body.get("files") or {})
        make_target = unit.render_target(target)
        response = build(unit, make_target)
        response["rendered_md"] = (
            read_if_exists(unit.render_path(target)) if response["ok"] else None
        )
    return jsonify(response)


@app.post("/api/compile")
def api_compile():
    """Write every buffer, then build whichever document previews this unit."""
    body = request.get_json(force=True)
    unit = unit_from_body(body)
    make_target = unit.preview_target()

    with BUILD_LOCK:
        write_files(unit, body.get("files") or {})

        if make_target is None:
            response = refusal(
                "(none)", "no preview for this module",
                f"{unit.module.label} declares no preview document in "
                f"modules/{unit.module.name}/editor.yaml, so there is nothing to compile.\n",
            )
        else:
            # A whole handout or round takes longer than a single problem.
            response = build(unit, make_target, timeout=600)
            built = REPO_ROOT / make_target
            if response["ok"] and built.is_file():
                cached = unit.cached_pdf()
                cached.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(built, cached)

        response["has_pdf"] = unit.cached_pdf().is_file()
    return jsonify(response)


@app.get("/api/pdf/<module>/<path:unit>")
def api_pdf(module, unit):
    resolved = Unit(module, unit, request.args.get("lang"))
    cached = resolved.cached_pdf()
    if not cached.is_file():
        raise BadRequest("Nothing compiled yet for this unit.")
    response = send_file(cached, mimetype="application/pdf")
    response.headers["Cache-Control"] = "no-store"
    return response


# --- style checker ----------------------------------------------------------

VIOLATION_RE = re.compile(r"^File (?P<file>.+) line (?P<line>\d+): (?P<message>.+)$")


def parse_mdcheck_output(stdout):
    lines = stdout.splitlines()
    violations = []
    i = 0
    while i < len(lines):
        m = VIOLATION_RE.match(lines[i])
        if m and i + 2 < len(lines):
            marker = lines[i + 2]
            column = marker.index("^") if "^" in marker else None
            violations.append({
                "line": int(m.group("line")),
                "column": column,
                "message": m.group("message"),
                "source_line": lines[i + 1],
            })
            i += 3
        else:
            i += 1
    return violations


@app.post("/api/lint")
def api_lint():
    body = request.get_json(force=True)
    unit = unit_from_body(body)
    target = body.get("target")
    unit.source_path(target)        # validates
    if unit.is_aux(target):
        raise BadRequest("The style checker only reads Markdown.")

    render_path = unit.render_path(target)
    if not render_path.is_file():
        raise BadRequest("Render the file before linting it.")

    with BUILD_LOCK:
        result = subprocess.run(
            ["uv", "run", "python", "core/markdown-check.py",
             render_path.relative_to(REPO_ROOT).as_posix(), "-v"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )

    stdout = ANSI_RE.sub("", result.stdout)
    return jsonify({
        "ok": result.returncode == 0,
        "violations": parse_mdcheck_output(stdout),
        "stdout": stdout,
        "stderr": ANSI_RE.sub("", result.stderr),
        "returncode": result.returncode,
    })


def main():
    parser = argparse.ArgumentParser(description="Local DGS problem source/render editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
