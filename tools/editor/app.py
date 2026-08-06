import argparse
import re
import shutil
import subprocess
import threading
from pathlib import Path

from flask import Flask, jsonify, request, render_template, send_file

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "source" / "naboj"

# Which directory a target's source lives in, mirroring the two rule families in
# `modules/naboj/module.mk`: translatable files sit in `<problem>/<language>/`, the rest
# directly in `<problem>/`. `answer-extra` is translated -- it is covered by the
# NABOJ_TRANSLATABLE loop and its file lives under the language directory.
TRANSLATABLE_TARGETS = ("problem", "problem-extra", "solution", "answer-extra")
NONTRANSLATABLE_TARGETS = ("answer", "answer-also", "answer-interval")

# Display order: the order the standalone document prints them in.
ORDERED_TARGETS = (
    "problem", "problem-extra", "solution",
    "answer", "answer-extra", "answer-also", "answer-interval",
)
ALL_TARGETS = frozenset(TRANSLATABLE_TARGETS) | frozenset(NONTRANSLATABLE_TARGETS)

# Last known-good preview PDFs. `double_xelatex` runs with `-halt-on-error`, so a failed
# compile can leave a truncated file in `output/`; serving a copy means a broken edit keeps
# showing the previous render beside the error log instead of a blank pane.
PDF_CACHE = REPO_ROOT / "build" / ".editor-preview"

LANG_RE = re.compile(r"^[a-z]{2,3}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b[()][A-Za-z0-9]")

BUILD_LOCK = threading.Lock()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


class BadRequest(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({"error": e.message}), 400


def resolve_problem_dir(key):
    if not key or ".." in key.split("/"):
        raise BadRequest(f"Invalid problem key: {key!r}")
    problem_dir = (SOURCE_ROOT / key).resolve()
    if not problem_dir.is_relative_to(SOURCE_ROOT.resolve()):
        raise BadRequest(f"Invalid problem key: {key!r}")
    if not (problem_dir / "meta.yaml").is_file() or problem_dir.parent.name != "problems":
        raise BadRequest(f"No such problem: {key!r}")
    return problem_dir


def available_langs(problem_dir):
    return sorted(
        d.name for d in problem_dir.iterdir()
        if d.is_dir() and (d / "problem.md").is_file()
    )


def validate_lang(problem_dir, lang):
    if not lang or not LANG_RE.match(lang) or lang not in available_langs(problem_dir):
        raise BadRequest(f"Invalid or unavailable language: {lang!r}")


def validate_target(target):
    if target not in ALL_TARGETS:
        raise BadRequest(f"Invalid target: {target!r}")


def source_path_for_target(problem_dir, lang, target):
    if target in TRANSLATABLE_TARGETS:
        return problem_dir / lang / f"{target}.md"
    return problem_dir / f"{target}.md"


def render_path_for_target(key, lang, target):
    return REPO_ROOT / "render" / "naboj" / key / lang / f"{target}.md"


def read_if_exists(path):
    return path.read_text() if path.is_file() else None


def list_problems():
    problems = []
    for meta_path in sorted(SOURCE_ROOT.rglob("meta.yaml")):
        problem_dir = meta_path.parent
        if problem_dir.parent.name != "problems":
            continue  # venue/constants/language config, not an actual problem
        key = problem_dir.relative_to(SOURCE_ROOT).as_posix()
        problems.append({"key": key, "langs": available_langs(problem_dir)})
    return problems


def existing_targets(problem_dir, lang):
    """
    Every target this problem actually has a file for, in document order. The editor opens
    all of them at once, so it needs the list rather than a fixed pair plus extras.
    """
    return [
        target for target in ORDERED_TARGETS
        if lang and source_path_for_target(problem_dir, lang, target).is_file()
    ]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/problems")
def api_problems():
    return jsonify(list_problems())


@app.get("/api/problem/<path:key>")
def api_problem(key):
    problem_dir = resolve_problem_dir(key)
    langs = available_langs(problem_dir)
    lang = request.args.get("lang") or (langs[0] if langs else None)

    if lang:
        validate_lang(problem_dir, lang)

    targets = existing_targets(problem_dir, lang)
    return jsonify({
        "key": key,
        "langs": langs,
        "lang": lang,
        "targets": targets,
        "meta_yaml": read_if_exists(problem_dir / "meta.yaml"),
        "files": {
            target: read_if_exists(source_path_for_target(problem_dir, lang, target))
            for target in targets
        },
    })


def run_make(target, *, timeout=60):
    return subprocess.run(
        ["uv", "run", "make", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def make_result(target, result):
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "command": f"make {target}",
        "stdout": ANSI_RE.sub("", result.stdout),
        "stderr": ANSI_RE.sub("", result.stderr),
    }


def write_files(problem_dir, lang, files):
    """
    Write back every buffer the editor sent. All of a problem's files are open at once, so a
    save or a compile has to flush all the dirty ones -- compiling only the active tab would
    silently preview a mixture of edited and stale text.
    """
    if files.get("meta_yaml") is not None:
        (problem_dir / "meta.yaml").write_text(files["meta_yaml"])

    for target, content in (files.get("targets") or {}).items():
        validate_target(target)
        source_path = source_path_for_target(problem_dir, lang, target)
        if not source_path.is_file():
            raise BadRequest(f"Refusing to create a new file: {target}.md does not exist")
        source_path.write_text(content)


def request_problem(body):
    """Resolve and validate the `key`/`lang` every endpoint below starts with."""
    key = body.get("key")
    lang = body.get("lang")
    problem_dir = resolve_problem_dir(key)
    validate_lang(problem_dir, lang)
    return key, lang, problem_dir


@app.post("/api/save")
def api_save():
    body = request.get_json(force=True)
    key, lang, problem_dir = request_problem(body)

    with BUILD_LOCK:
        write_files(problem_dir, lang, body.get("files") or {})

    return jsonify({"ok": True})


@app.post("/api/render")
def api_render():
    body = request.get_json(force=True)
    key, lang, problem_dir = request_problem(body)
    target = body.get("target")
    validate_target(target)

    with BUILD_LOCK:
        write_files(problem_dir, lang, body.get("files") or {})

        make_target = f"render/naboj/{key}/{lang}/{target}.md"
        response = make_result(make_target, run_make(make_target))
        response["rendered_md"] = (
            read_if_exists(render_path_for_target(key, lang, target)) if response["ok"] else None
        )

    return jsonify(response)


def cached_pdf_path(key, lang):
    return PDF_CACHE / key / lang / "standalone.pdf"


@app.post("/api/compile")
def api_compile():
    """Write every buffer, then build the standalone one-problem PDF for the preview pane."""
    body = request.get_json(force=True)
    key, lang, problem_dir = request_problem(body)

    with BUILD_LOCK:
        write_files(problem_dir, lang, body.get("files") or {})

        make_target = f"output/naboj/{key}/{lang}/standalone.pdf"
        response = make_result(make_target, run_make(make_target, timeout=300))

        built = REPO_ROOT / make_target
        if response["ok"] and built.is_file():
            cached = cached_pdf_path(key, lang)
            cached.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built, cached)

        response["has_pdf"] = cached_pdf_path(key, lang).is_file()

    return jsonify(response)


@app.get("/api/pdf/<path:key>/<lang>")
def api_pdf(key, lang):
    problem_dir = resolve_problem_dir(key)
    validate_lang(problem_dir, lang)

    cached = cached_pdf_path(key, lang)
    if not cached.is_file():
        raise BadRequest("Nothing compiled yet for this problem and language.")

    response = send_file(cached, mimetype="application/pdf")
    response.headers["Cache-Control"] = "no-store"
    return response


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
    key, lang, _ = request_problem(body)
    target = body.get("target")
    validate_target(target)

    render_path = render_path_for_target(key, lang, target)
    if not render_path.is_file():
        raise BadRequest("Render the file before linting it.")

    rel_path = render_path.relative_to(REPO_ROOT).as_posix()

    with BUILD_LOCK:
        result = subprocess.run(
            ["uv", "run", "python", "core/markdown-check.py", rel_path, "-v"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

    stdout = ANSI_RE.sub("", result.stdout)
    stderr = ANSI_RE.sub("", result.stderr)
    return jsonify({
        "ok": result.returncode == 0,
        "violations": parse_mdcheck_output(stdout),
        "stdout": stdout,
        "stderr": stderr,
        "returncode": result.returncode,
    })


def main():
    parser = argparse.ArgumentParser(description="Local Náboj problem source/render editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
