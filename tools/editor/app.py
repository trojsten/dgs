import argparse
import re
import subprocess
import threading
from pathlib import Path

from flask import Flask, jsonify, request, render_template

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "source" / "naboj"

TRANSLATABLE_TARGETS = {"problem", "solution", "problem-extra"}
NONTRANSLATABLE_TARGETS = {"answer", "answer-also", "answer-interval", "answer-extra"}
ALL_TARGETS = TRANSLATABLE_TARGETS | NONTRANSLATABLE_TARGETS

LANG_RE = re.compile(r"^[a-z]{2,3}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b[()][A-Za-z0-9]")

BUILD_LOCK = threading.Lock()

app = Flask(__name__)


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
    if not (problem_dir / "meta.yaml").is_file():
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
        key = problem_dir.relative_to(SOURCE_ROOT).as_posix()
        langs = available_langs(problem_dir)
        optional = [
            t for t in ("answer", "answer-also", "answer-interval")
            if (problem_dir / f"{t}.md").is_file()
        ]
        problems.append({"key": key, "langs": langs, "optional_targets": optional})
    return problems


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

    data = {
        "key": key,
        "langs": langs,
        "lang": lang,
        "meta_yaml": read_if_exists(problem_dir / "meta.yaml"),
        "preamble_md": read_if_exists(problem_dir / "preamble.md"),
        "answer_md": read_if_exists(problem_dir / "answer.md"),
        "answer_also_md": read_if_exists(problem_dir / "answer-also.md"),
        "answer_interval_md": read_if_exists(problem_dir / "answer-interval.md"),
        "problem_md": None,
        "solution_md": None,
        "problem_extra_md": None,
    }

    if lang:
        validate_lang(problem_dir, lang)
        lang_dir = problem_dir / lang
        data["problem_md"] = read_if_exists(lang_dir / "problem.md")
        data["solution_md"] = read_if_exists(lang_dir / "solution.md")
        data["problem_extra_md"] = read_if_exists(lang_dir / "problem-extra.md")

    return jsonify(data)


def run_make(target):
    return subprocess.run(
        ["uv", "run", "make", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


@app.post("/api/render")
def api_render():
    body = request.get_json(force=True)
    key = body.get("key")
    lang = body.get("lang")
    target = body.get("target")
    files = body.get("files") or {}

    problem_dir = resolve_problem_dir(key)
    validate_lang(problem_dir, lang)
    validate_target(target)

    with BUILD_LOCK:
        if "meta_yaml" in files:
            (problem_dir / "meta.yaml").write_text(files["meta_yaml"])
        if "preamble_md" in files:
            (problem_dir / "preamble.md").write_text(files["preamble_md"])
        if "content" in files:
            source_path_for_target(problem_dir, lang, target).write_text(files["content"])

        make_target = f"render/naboj/{key}/{lang}/{target}.md"
        result = run_make(make_target)

        response = {
            "ok": result.returncode == 0,
            "stdout": ANSI_RE.sub("", result.stdout),
            "stderr": ANSI_RE.sub("", result.stderr),
            "returncode": result.returncode,
            "rendered_md": None,
        }
        if response["ok"]:
            render_path = render_path_for_target(key, lang, target)
            response["rendered_md"] = read_if_exists(render_path)

    return jsonify(response)


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
    key = body.get("key")
    lang = body.get("lang")
    target = body.get("target")

    problem_dir = resolve_problem_dir(key)
    validate_lang(problem_dir, lang)
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
