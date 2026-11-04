r"""
What the build invokes in place of `python -m …`. Run it with `-S`.

    .venv/bin/python3 -S tools/runner/client.py -m modules.naboj.builder.renderer sk …
    .venv/bin/python3 -S tools/runner/client.py pandoc.py --format latex sk …

The argument list after the script is **exactly what `python` itself would have taken**, so any
command in `build.ninja` can be run by hand by deleting `-S tools/runner/client.py` from it, and
`DGS_NO_DAEMON=1` does that for you -- the client `exec`s the real interpreter and nothing else
about the invocation changes.

It imports four stdlib modules and nothing else, because its own startup is the floor on what
this whole exercise can save: 14 ms here against 445 ms for the renderer. `-S` skips `site`, so
the venv's packages are not on the path and must not be wanted. Everything else -- `fcntl`,
`subprocess`, `time` -- is imported inside `spawn`, which runs once per build at most.

**Every failure before the daemon acknowledges falls back to running the job here.** No daemon,
a refused socket, one too old to answer, one that died holding the request: each ends in
`os.execv` of the real interpreter, so this cannot break a build, only slow it back down to
where it was. After the acknowledgement the opposite rule applies -- see `request`.
"""
import os
import socket
import struct
import sys

#: The checkout this file belongs to, so that the client works from a subdirectory and two
#: checkouts never share a daemon. `tools/runner/client.py` is three directories down.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#: Under `build/`, which is already ignored and already swept. A path too long for a Unix
#: socket -- they are capped near 108 bytes -- simply fails to bind and to connect, and the
#: build falls back to plain interpreters, which is the right way for that to go wrong. The
#: override is what lets a test have a daemon of its own rather than restarting yours.
SOCKET = os.environ.get('DGS_RUNNER_SOCKET') or os.path.join(ROOT, 'build', '.dgsd', 'sock')
LOCK = SOCKET + '.lock'
#: Long enough for the daemon to bind, which it does before importing anything; a client that
#: connects during the import simply waits in `accept`. Not long enough to matter if the
#: daemon cannot start at all, which `spawn` notices directly anyway.
SPAWN_TIMEOUT = 20.0
#: How long a daemon may take to acknowledge before we give up on it and do the job here. The
#: job itself is then given no limit at all: a volume booklet legitimately takes minutes.
READY_TIMEOUT = 60.0
#: The daemon's "I have your descriptors, your directory and your environment, and I am about
#: to run this". See `request`.
READY = b'\x01'


def direct(argv):
    """Be `python` after all. Does not return."""
    os.execv(sys.executable, [sys.executable, *argv])


def connect():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(READY_TIMEOUT)
    sock.connect(SOCKET)
    return sock


def spawn():
    """
    Start a daemon, under a lock so that eight parallel clients do not start eight of them.

    Whoever takes the lock tries to connect first, because by then the daemon the previous
    holder started is usually up and nothing needs starting at all. A daemon that dies on the
    way up is noticed as it dies rather than waited out, so a broken one costs each client the
    half second it takes to fail, not `SPAWN_TIMEOUT`.
    """
    import fcntl
    import subprocess
    import time

    os.makedirs(os.path.dirname(SOCKET) or '.', exist_ok=True)
    with open(LOCK, 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return connect()
        except OSError:
            pass
        daemon = subprocess.Popen(
            [sys.executable, '-m', 'tools.runner.server'], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        deadline = time.monotonic() + SPAWN_TIMEOUT
        while time.monotonic() < deadline:
            try:
                return connect()
            except OSError:
                if daemon.poll() is not None:
                    return None
                time.sleep(0.02)
    return None


def request(sock, argv):
    """
    One job: the working directory, the environment and the argument list, with our own three
    streams passed as descriptors so that the child writes straight to them.

    Fields are NUL-separated and the length of `argv` is sent before it, so the environment
    needs no delimiter of its own. Nothing here can hold a NUL: a command line and an
    environment are both NUL-terminated strings to begin with.

    **`None` means the job has not started** -- nothing acknowledged, or the daemon died
    holding the request -- and the caller may safely run it here instead. Once the
    acknowledgement is in, the rule inverts: anything that goes wrong is the job's own failure
    and is reported as one, because falling back then would run a half-finished job a second
    time.
    """
    fields = [os.getcwd(), str(len(argv)), *argv,
              *(f'{key}={value}' for key, value in os.environ.items())]
    payload = '\0'.join(fields).encode()
    try:
        # The length goes in the **same** `sendmsg` as the descriptors, not in a `sendall`
        # before it. On a stream socket the ancillary data rides on one byte of the stream and
        # is delivered to whichever `recvmsg` consumes that byte -- so a plain `recv` of a
        # separate header can coalesce the first payload byte with it, and the descriptors are
        # closed without a word. One send, one `recv_fds` on the far side, no race.
        socket.send_fds(sock, [struct.pack('<I', len(payload)) + payload], [0, 1, 2])
        if sock.recv(1) != READY:
            return None
    except OSError:
        return None

    sock.settimeout(None)
    held = b''
    while len(held) < 4:
        try:
            piece = sock.recv(4 - len(held))
        except OSError:
            piece = b''
        if not piece:
            # Its output has already gone to our own streams, so whatever it managed is on the
            # terminal; what is lost is the status. 70 is `EX_SOFTWARE`, and a failure here is
            # the only honest answer -- re-running could repeat half a job.
            print('dgs runner: the job died without reporting a status', file=sys.stderr)
            return 70
        held += piece
    return struct.unpack('<i', held)[0]


def main() -> int:
    argv = sys.argv[1:]
    if not argv or os.environ.get('DGS_NO_DAEMON'):
        direct(argv)

    try:
        sock = connect()
    except OSError:
        sock = spawn()
    if sock is None:
        direct(argv)

    with sock:
        code = request(sock, argv)
    if code is None:
        direct(argv)
    return code


if __name__ == '__main__':
    sys.exit(main())
