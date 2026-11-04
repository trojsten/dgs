r"""
The warm interpreter. Started by `client.py` when nothing is listening; never started by hand
in the course of a build.

    python -m tools.runner.server            run in the foreground, to watch it
    python -m tools.runner.server --stop     tell a running one to go away

It imports the build's Python once and forks a child per job. The child inherits every parsed
locale, the pint registry and whatever Jinja has cached, which is the whole point, and inherits
them *copy-on-write*, so nothing it does to them outlives it. See `__init__.py`.

**It must hold no threads.** `import numpy` spawns an OpenBLAS pool -- 0.57 s of CPU at 630 %,
for a build that does no linear algebra -- and forking a process whose threads hold locks is
the classic way to a child that deadlocks on its first allocation. The variables below are set
before the first import for that reason: this is a correctness measure and the CPU it saves is
incidental.

**Staleness is checked in the parent, before every fork.** A hash of every `.py`, `.yaml` and
`.lua` under `core/`, `modules/` and `tools/` -- 176 files, 1.2 ms -- stands for what was
imported. When it moves, the daemon unlinks its socket and exits rather than answering with
code that is no longer on disk; the client whose request met the change runs the job itself,
and the next one starts a fresh daemon. A job already running when a file changes is a race
`make` has too.

**One thing a job does not inherit: the build's process group.** The daemon is its own session,
so interrupting `ninja` kills the clients and leaves their jobs to finish into descriptors
nobody is reading any more. They exit within a second or two and Ninja re-runs the edges whose
commands never reported, which is what it does for an interrupted build anyway.
"""
from __future__ import annotations

import os

# Before anything imports numpy. See the module docstring: this is what makes the fork safe.
for _variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_variable] = '1'

import contextlib
import dataclasses
import hashlib
import importlib
import io
import locale
import runpy
import socket
import struct
import sys
import traceback

#: The checkout this file belongs to. Everything below is anchored to it rather than to the
#: working directory, because the daemon outlives whichever one it was started from -- and a
#: fingerprint taken relative to the wrong directory would find no files and never go stale,
#: which is the one way this could serve code that is no longer on disk.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOCKET = os.environ.get('DGS_RUNNER_SOCKET') or os.path.join(ROOT, 'build', '.dgsd', 'sock')

#: No client for this long and there is no build going on. Cheap to start again.
IDLE = 1800.0
#: How often `accept` is interrupted to ask whether the socket is still ours, which is how
#: `--stop` -- and `ninja -t clean`, and `rm -rf build/` -- is noticed rather than waited out.
TICK = 5.0
#: What a request may hold. A command line and an environment, no more.
LIMIT = 1 << 20
#: Sent once the child holds the job's descriptors, directory and environment and is about to
#: run it. It is what divides "the daemon never started this" from "this failed".
READY = b'\x01'

#: Imported at startup so that the first job is as fast as the second.
#:
#: **Libraries only.** Eight of the builders -- `core/builder/i18n.py`, naboj's `language.py`
#: and `venue.py`, seminar's `round.py`, scholar's three -- end with a bare
#: `BuilderX().build_templates()` at module level rather than under an `if __name__`, so
#: importing one *runs* it: the first draft of this list printed an argparse usage message and
#: took the daemon down with it. What they cost is in the modules underneath, which is what is
#: named here. A module that is not there -- scholar and seminar are optional checkouts -- is
#: skipped, and the job that wants it imports it itself, once.
#:
#: **Nor the modules the build runs as `__main__`**, the three `builder.renderer` among them.
#: `runpy` warns when asked to execute a module already in `sys.modules`, and it is right to:
#: the job would hold two copies of every class in that file. Preloading buys nothing there
#: anyway -- the expense is `core.builder.renderer` underneath, and executing the entry module
#: itself is a handful of class statements.
PRELOAD = (
    'core.builder.jinja',
    'core.builder.builder',
    'core.builder.convertor',
    'core.builder.standalone',
    'core.builder.renderer',
    'modules.naboj.builder.builder',
    'modules.naboj.builder.contexts',
    'modules.seminar.builder.builder',
    'modules.seminar.builder.context',
    'modules.scholar.builder.builder',
    'modules.scholar.builder.contexts',
)

#: Where the code is. Templates are deliberately absent: a `.jtex` is a dependency of the build
#: graph, not of the interpreter, and changing one must not cost a restart.
SOURCES = ('core', 'modules', 'tools')
SCRIPTS = ('pandoc.py', 'standalone.py')
#: Directories whose contents say nothing about what was imported.
SKIPPED = {'__pycache__', 'tests', 'node_modules'}
SUFFIXES = ('.py', '.yaml', '.lua')


def watched():
    """Every file whose contents could be in this process's memory."""
    for name in SOURCES:
        for directory, children, files in os.walk(os.path.join(ROOT, name)):
            children[:] = [c for c in children if c not in SKIPPED and not c.startswith('.')]
            for found in files:
                if found.endswith(SUFFIXES):
                    yield os.path.join(directory, found)
    for name in SCRIPTS:
        yield os.path.join(ROOT, name)


def fingerprint() -> str:
    """What was imported, as far as the file system can say: name, mtime and size of each."""
    digest = hashlib.blake2b(digest_size=16)
    for path in sorted(watched()):
        try:
            stat = os.stat(path)
        except OSError:
            digest.update(f'{path}\0gone\0'.encode())
        else:
            digest.update(f'{path}\0{stat.st_mtime_ns}\0{stat.st_size}\0'.encode())
    return digest.hexdigest()


def preload() -> None:
    """
    Best effort, and `BaseException` rather than `ImportError`: a module that insists on
    parsing arguments or calling `sys.exit` at import must cost one slow job, never the daemon.
    """
    for name in PRELOAD:
        with contextlib.suppress(BaseException):
            importlib.import_module(name)


@dataclasses.dataclass(frozen=True, slots=True)
class Request:
    """One job as the client described it, and the three descriptors it sent with it."""

    cwd: str
    argv: list[str]
    environment: dict[str, str]
    descriptors: list[int]

    @classmethod
    def read(cls, connection) -> Request | None:
        """
        `None` for anything malformed, with the descriptors closed on the way out. The child
        is about to exit either way, but a half-read request must not go on holding the
        client's three streams open while it does.
        """
        held, descriptors, _, _ = socket.recv_fds(connection, 65536, 3)
        request = cls.parse(connection, held, descriptors)
        if request is None:
            for descriptor in descriptors:
                os.close(descriptor)
        return request

    @classmethod
    def parse(cls, connection, held: bytes, descriptors: list[int]) -> Request | None:
        """
        The rest of the stream, and the fields in it. The first `recv` is the one that carried
        the descriptors and may have carried any amount of the payload with them, so what is
        left is read here -- plainly, the ancillary data being long since delivered.
        """
        if len(held) < 4 or len(descriptors) != 3:
            return None
        try:
            (length,) = struct.unpack('<I', held[:4])
            if length > LIMIT:
                return None
            held = held[4:]
            while len(held) < length:
                piece = connection.recv(length - len(held))
                if not piece:
                    return None
                held += piece

            fields = held.decode().split('\0')
            count = int(fields[1])
            return cls(cwd=fields[0], argv=fields[2:2 + count],
                       environment=dict(entry.split('=', 1)
                                        for entry in fields[2 + count:] if '=' in entry),
                       descriptors=descriptors)
        except (OSError, UnicodeDecodeError, ValueError, IndexError, struct.error):
            return None

    def become(self) -> None:
        """Make this child look like the process the client would otherwise have started."""
        for target, descriptor in enumerate(self.descriptors):
            os.dup2(descriptor, target)
            os.close(descriptor)
        # Rebuilt rather than reused: the daemon's own `sys.stdout` settled its buffering
        # against whatever it was started with -- `/dev/null`, so block-buffered -- and a job
        # whose output is a terminal wants that decision taken again. UTF-8 outright, because
        # every file in this repository is UTF-8 and the alternative is that a job's output
        # depends on the locale of the terminal the daemon happened to be started from half an
        # hour ago, which is the one thing a long-lived process must not let happen.
        sys.stdin = io.TextIOWrapper(io.FileIO(0, 'r', closefd=False), encoding='utf-8')
        sys.stdout = io.TextIOWrapper(io.FileIO(1, 'w', closefd=False), encoding='utf-8',
                                      line_buffering=os.isatty(1))
        sys.stderr = io.TextIOWrapper(io.FileIO(2, 'w', closefd=False), encoding='utf-8',
                                      errors='backslashreplace', line_buffering=True)

        os.environ.clear()
        os.environ.update(self.environment)
        # The client's locale and not the daemon's, for the same reason: `Path.open()`
        # throughout the builders takes its encoding from it.
        with contextlib.suppress(locale.Error):
            locale.setlocale(locale.LC_ALL, '')
        os.chdir(self.cwd)

    def execute(self) -> int:
        """`python -m module …` or `python script.py …`, as the interpreter would read it."""
        try:
            if self.argv[0] == '-m':
                sys.argv = [self.argv[1], *self.argv[2:]]
                runpy.run_module(self.argv[1], run_name='__main__', alter_sys=True)
            else:
                sys.argv = list(self.argv)
                runpy.run_path(self.argv[0], run_name='__main__')
        except SystemExit as exit:
            if exit.code is None or isinstance(exit.code, int):
                return exit.code or 0
            # What the interpreter does with `sys.exit('…')`, which nothing here writes today.
            print(exit.code, file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130
        except Exception:  # noqa: BLE001 -- the top level of a process, and it behaves like
            # one: whatever the job raised is printed and becomes a status, because there is
            # nobody above to handle it and letting it reach the daemon would end the build.
            traceback.print_exc()
            return 1
        return 0


def serve(connection) -> None:
    """The child, which never returns from here."""
    code = 70
    try:
        request = Request.read(connection)
        if request is not None:
            request.become()
            # In place and about to run, so from here on a client that loses the connection
            # must report a failure rather than run the job itself. Before this byte it may
            # safely fall back; after it, falling back would run the job twice.
            connection.sendall(READY)
            code = request.execute()
    finally:
        for stream in (sys.stdout, sys.stderr):
            with contextlib.suppress(Exception):
                stream.flush()
        with contextlib.suppress(OSError):
            connection.sendall(struct.pack('<i', code))
        with contextlib.suppress(OSError):
            connection.close()
        os._exit(code)


def listen() -> tuple[socket.socket, int] | None:
    """
    The listening socket and the inode of the path it is bound to.

    `None` is the answer to every reason there should be no daemon here, and the client reads
    all of them the same way -- it runs the job itself. Somebody else is already serving, which
    is how a duplicate from a spawn race retires itself; or the path cannot be bound at all,
    a Unix socket name being capped near 108 bytes.
    """
    os.makedirs(os.path.dirname(SOCKET) or '.', exist_ok=True)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(SOCKET)
    except OSError:
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(SOCKET)
        except OSError:
            pass
        else:
            probe.close()
            return None
        # Nothing was listening, so whatever is there is a corpse and may be cleared.
        with contextlib.suppress(OSError):
            os.unlink(SOCKET)
        try:
            listener.bind(SOCKET)
        except OSError:
            return None
    listener.listen(64)
    # The inode of the **path**, not of the socket: `fstat` on a bound socket descriptor
    # reports its node in the socket filesystem, which says nothing about the path at all.
    return listener, os.stat(SOCKET).st_ino


def ours(inode: int) -> bool:
    """Is the socket we bound still the socket at that path? `--stop` is what makes it not."""
    try:
        return os.stat(SOCKET).st_ino == inode
    except OSError:
        return False


def reap() -> None:
    """Children that have finished, collected where no signal handler has to be involved."""
    with contextlib.suppress(ChildProcessError):
        while os.waitpid(-1, os.WNOHANG)[0]:
            pass


def main() -> int:
    if '--stop' in sys.argv[1:]:
        with contextlib.suppress(OSError):
            os.unlink(SOCKET)
        return 0

    bound = listen()
    if bound is None:
        return 0
    listener, inode = bound
    held = fingerprint()
    preload()
    listener.settimeout(TICK)

    try:
        idle = 0.0
        while True:
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                reap()
                idle += TICK
                if idle >= IDLE or not ours(inode):
                    return 0
                continue
            idle = 0.0
            reap()
            with connection:
                if fingerprint() != held:
                    return 0
                if os.fork() == 0:
                    listener.close()
                    serve(connection)
    finally:
        if ours(inode):
            with contextlib.suppress(OSError):
                os.unlink(SOCKET)


if __name__ == '__main__':
    sys.exit(main())
