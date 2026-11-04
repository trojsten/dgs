r"""
`build.ninja` into existence, and then Ninja -- which is the one step Ninja cannot do itself.

The graph is generated and gitignored, so a fresh clone has none and `ninja` stops at

    ninja: error: loading 'build.ninja': No such file or directory

naming a file nobody has heard of and saying nothing about a generator. Unlike `make`, which
finds a `Makefile` checked into the tree, Ninja has no bootstrap: the `generator = 1` edge keeps
an *existing* graph current -- it depends on `generate.py`, `writer.py` and every source
directory the graph was read from, so adding a problem or a language re-runs it mid-build -- but
it cannot write the first one.

So every entry point calls `ensure_graph` before it calls Ninja. There are two: the editor, from
`tools/editor/app.py`'s `run_build`, and the command line, through `./dgs-build`.

**The scope is `all`, deliberately.** A graph generated for one volume answers `unknown target`
for every other, which reads exactly like a broken build to somebody who was never told a graph
has a scope -- and regenerating the whole repository costs about a second. A narrower graph is
for someone who has asked for one, by running `tools.ninja.generate` themselves.

**Only absence is ours to fix.** This never regenerates a graph that is merely old: that is the
generator edge's job, it knows what it read, and second-guessing it here would put two different
answers to "is the graph stale" in the tree.
"""
import os
import pathlib
import subprocess
import sys

#: This file is `<root>/tools/ninja/bootstrap.py`.
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def ensure_graph(root=ROOT, *, env=None, python=None):
    """
    Generate `build.ninja` if it is not there. `None` when nothing was wrong, else the failure.

    `python` is the interpreter to generate with, and defaults to the one running this. The
    generator imports nothing outside the standard library, but the project asks for 3.14 and a
    system `python3` may be older, so the caller that knows better passes it.
    """
    root = pathlib.Path(root)
    graph = root / 'build.ninja'
    if graph.is_file():
        return None
    result = subprocess.run(
        [python or sys.executable, '-m', 'tools.ninja.generate',
         '--scope', 'all', '-o', str(graph)],
        check=False, cwd=root, capture_output=True, text=True, timeout=300, env=env)
    return None if result.returncode == 0 else result


def main(argv=None):
    """
    `./dgs-build <target> …`: make sure there is a graph, then become Ninja.

    How to invoke Ninja is `capabilities.probe_python_launcher`'s answer rather than one of our
    own -- it is the same question the editor asks, and two answers to it would drift. That
    module is under `tools/editor/` because the editor is what made it worth writing, and it
    probes the machine rather than serving a page, so this is not a layering violation.

    `exec` rather than a subprocess, so Ninja owns the terminal: its one-line progress display
    needs a tty, and Ctrl-C has to reach it rather than us.
    """
    argv = sys.argv[1:] if argv is None else argv
    sys.path.insert(0, str(ROOT))
    from tools.editor import capabilities

    launcher = capabilities.probe_python_launcher()
    env = dict(os.environ)
    if launcher['path_prefix']:
        env['PATH'] = launcher['path_prefix'] + os.pathsep + env.get('PATH', '')

    if (failed := ensure_graph(ROOT, env=env)) is not None:
        sys.stderr.write(f'could not generate build.ninja:\n{failed.stderr}')
        return 1

    os.chdir(ROOT)
    try:
        os.execvpe(launcher['argv'][0], [*launcher['argv'], *argv], env)
    except FileNotFoundError:
        sys.stderr.write(
            f"{launcher['argv'][0]}: not found. "
            f"{' or '.join(capabilities.INSTALL['ninja'])}\n")
        return 127


if __name__ == '__main__':
    sys.exit(main())
