r"""
The warm runner, `tools/runner/`.

Each test runs a real client against a real daemon, because what is worth asserting here is
exactly what a unit test of the pieces would stub out: that descriptors reach the child, that
an exit status comes back, that the environment and the working directory are the client's and
not the daemon's. The daemon is given a socket of its own through `DGS_RUNNER_SOCKET`, so a
test run never restarts -- or inherits the state of -- the one serving a build in the next
terminal.

The job every test runs is `core.builder.reference`, which is core's own, needs no content
repository, and is cheap: `--check` reads `docs/filters.md` and says whether it is stale.
"""
import os
import pathlib
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CLIENT = ('-S', 'tools/runner/client.py')
#: A job that exists in a bare checkout, writes to stdout, and takes an argument that decides
#: whether it succeeds.
JOB = ('-m', 'core.builder.reference', '--check')


@pytest.fixture
def runner(tmp_path):
    """A client bound to a daemon of this test's own, stopped however the test ends."""
    environment = dict(os.environ, DGS_RUNNER_SOCKET=str(tmp_path / 'sock'))

    def run(*arguments, **extra):
        return subprocess.run([sys.executable, *CLIENT, *arguments], check=False,
                              cwd=ROOT, capture_output=True, text=True,
                              env=dict(environment, **extra.pop('env', {})), **extra)

    yield run
    subprocess.run([sys.executable, '-m', 'tools.runner.server', '--stop'],
                   cwd=ROOT, env=environment, capture_output=True, check=False)


def direct(*arguments):
    return subprocess.run([sys.executable, *arguments], check=False,
                          cwd=ROOT, capture_output=True, text=True)


class TestTheWarmRunner:
    def test_a_job_matches_the_interpreter_it_replaces(self, runner):
        """The whole contract: same stdout, same stderr, same status, warm or cold."""
        warm, cold = runner(*JOB), direct(*JOB)
        assert (warm.stdout, warm.stderr, warm.returncode) \
            == (cold.stdout, cold.stderr, cold.returncode)

    def test_a_second_job_reuses_the_daemon(self, runner):
        first = runner(*JOB)
        second = runner(*JOB)
        assert first.returncode == second.returncode
        assert first.stdout == second.stdout

    def test_a_failure_keeps_its_status_and_its_complaint(self, runner):
        """`--check` is not the point; a status other than 0 surviving the socket is."""
        warm = runner('-m', 'core.builder.reference', '--nonsense')
        cold = direct('-m', 'core.builder.reference', '--nonsense')
        assert warm.returncode == cold.returncode != 0
        assert warm.stderr == cold.stderr

    def test_the_fallback_is_the_plain_interpreter(self, runner):
        """`DGS_NO_DAEMON` must leave nothing behind, because it never connects."""
        warm = runner(*JOB, env={'DGS_NO_DAEMON': '1'})
        assert warm.returncode == direct(*JOB).returncode

    def test_a_daemon_holding_stale_code_retires_and_the_job_still_runs(self, runner,
                                                                        tmp_path):
        """
        The failure this exists to prevent is a daemon answering with code that is no longer
        on disk. It must refuse instead -- and refusing before the acknowledgement means the
        client runs the job itself, so the edit costs one slow job and nothing else.
        """
        runner(*JOB)
        socket = tmp_path / 'sock'
        assert socket.exists()

        watched = ROOT / 'core' / 'builder' / 'jinja.py'
        stat = watched.stat()
        try:
            os.utime(watched, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
            done = runner(*JOB)
        finally:
            os.utime(watched, ns=(stat.st_atime_ns, stat.st_mtime_ns))

        assert done.returncode == direct(*JOB).returncode
        deadline = time.monotonic() + 5
        while socket.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not socket.exists(), 'the stale daemon is still listening'

    def test_a_daemon_that_cannot_start_does_not_stop_the_build(self, tmp_path):
        """
        The job still runs, and in reasonable time. A Unix socket name is capped near 108
        bytes, so this one can be neither bound nor connected to; the daemon retires without
        a word and the client notices it go rather than waiting out `SPAWN_TIMEOUT`.
        """
        impossible = tmp_path / ('d' * 120) / 'sock'
        started = time.monotonic()
        done = subprocess.run([sys.executable, *CLIENT, *JOB], cwd=ROOT, check=False,
                              capture_output=True, text=True,
                              env=dict(os.environ, DGS_RUNNER_SOCKET=str(impossible)))
        assert (done.stdout, done.returncode) == (direct(*JOB).stdout, direct(*JOB).returncode)
        assert time.monotonic() - started < 10

    def test_the_child_takes_the_client_s_directory_and_environment(self, runner, tmp_path):
        """
        Not the daemon's. It is started from wherever the first client happened to be and
        lives for half an hour, so a job that inherited its directory or its environment would
        be right until the moment somebody built from somewhere else.

        The first call is what starts the daemon, from the repository root; the probe then
        runs from `tmp_path` and has to report `tmp_path` back.
        """
        runner(*JOB)

        probe = tmp_path / 'probe.py'
        probe.write_text('import os\nprint(os.getcwd())\nprint(os.environ["DGS_PROBE"])\n')
        answer = subprocess.run(
            [sys.executable, *CLIENT[:1], str(ROOT / CLIENT[1]), str(probe)], check=False,
            cwd=tmp_path, capture_output=True, text=True,
            env=dict(os.environ, DGS_RUNNER_SOCKET=str(tmp_path / 'sock'),
                     DGS_PROBE='from the client'))

        assert answer.returncode == 0, answer.stderr
        assert answer.stdout.splitlines() == [str(tmp_path), 'from the client']


class TestTheFingerprint:
    def test_it_moves_when_a_watched_file_does(self, tmp_path):
        """What makes the daemon refuse to answer with code that is no longer on disk."""
        from tools.runner import server

        before = server.fingerprint()
        assert before == server.fingerprint()

        watched = ROOT / 'core' / 'builder' / 'jinja.py'
        stat = watched.stat()
        try:
            os.utime(watched, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
            assert server.fingerprint() != before
        finally:
            os.utime(watched, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        assert server.fingerprint() == before

    def test_it_reads_the_code_and_not_the_sources(self):
        """A problem is not a dependency of the interpreter. Only what was imported is."""
        from tools.runner import server

        watched = {pathlib.Path(path) for path in server.watched()}
        assert ROOT / 'pandoc.py' in watched
        assert ROOT / 'core' / 'builder' / 'jinja.py' in watched
        assert not any(path.is_relative_to(ROOT / 'source') for path in watched)
        assert not any('__pycache__' in path.parts for path in watched)
        # A template is a dependency of the build graph, not of this process.
        assert not any(path.suffix == '.jtex' for path in watched)

    def test_it_is_anchored_to_the_checkout_and_not_to_the_directory(self, tmp_path,
                                                                     monkeypatch):
        """
        The daemon outlives the terminal it was started from. Taken relative to the working
        directory, the walk would find nothing from anywhere else and the fingerprint would
        never move again -- which is the one way this could go on serving deleted code.
        """
        from tools.runner import server

        assert all(pathlib.Path(path).is_absolute() for path in server.watched())
        before = server.fingerprint()
        monkeypatch.chdir(tmp_path)
        assert server.fingerprint() == before


class TestWhoMayTalkToTheDaemon:
    """
    The socket carries the job's three descriptors, the whole environment and the working
    directory, and `Request.execute` then runs whatever module or file the request names. So
    "who is at the other end" is not a detail of the transport, it is the authorisation.

    Two locks, checked here one each, because they fail differently: the **mode** on the socket,
    which one inherited umask can get wrong, and the **credentials**, which come from the kernel
    and cannot be spoofed. The client has its own half -- it refuses a socket somebody else owns
    rather than handing them the job.
    """

    def test_the_socket_is_private_to_its_owner(self, tmp_path, monkeypatch):
        """
        Mode 0600 whatever the umask is. It used to be `0777 & ~umask`, and a umask of 002 --
        the default on Debian and Ubuntu for a user in their own group -- made it
        group-writable: a bare `bind` under that umask gives 0775, measured.

        **What this covers is the pair, not each half.** `listen()` both narrows the umask round
        the `bind` and `chmod`s afterwards, and from outside only the end state is visible, so
        this would still pass with the umask handling removed. The umask is what closes the
        window *between* the two, which no test here can observe; it is cheap, it is the
        belt to the chmod's braces, and the reason it is there is written at the call site.
        """
        import importlib
        import stat

        monkeypatch.setenv('DGS_RUNNER_SOCKET', str(tmp_path / 'dgsd' / 'sock'))
        server = importlib.reload(importlib.import_module('tools.runner.server'))
        # The **real** umask, not a monkeypatched one: a stub `os.umask` would leave the process
        # umask alone and the assertion would then pass on the `chmod` alone, which is to say it
        # would pass with `listen()`'s umask handling deleted. 002 is the default on Debian and
        # Ubuntu for a user in their own group, and is what made the socket group-writable.
        previous = os.umask(0o002)
        try:
            listener, _inode = server.listen()
            assert stat.S_IMODE(os.stat(server.SOCKET).st_mode) == 0o600
            listener.close()
        finally:
            os.umask(previous)
            importlib.reload(server)

    def test_a_peer_running_as_somebody_else_is_refused(self, monkeypatch):
        """
        The firing case for the second lock, with the uid moved rather than the peer -- a test
        cannot become another user, and what is being checked is the comparison.
        """
        import socket as socketlib

        from tools.runner import server

        ours, theirs = socketlib.socketpair()
        try:
            assert server.peer_is_us(ours)                  # the quiet case: it really is us
            # The real uid first: a lambda calling `os.getuid()` would be calling itself.
            elsewhere = os.getuid() + 1
            monkeypatch.setattr(os, 'getuid', lambda: elsewhere)
            assert not server.peer_is_us(ours)
        finally:
            ours.close()
            theirs.close()

    def test_the_client_refuses_a_socket_somebody_else_owns(self, tmp_path, monkeypatch):
        """
        The client's half. In the image `build/` is mode 1777 so that a forced `--user` works,
        which is also where another uid could bind this name first; handing it the job would
        hand over the descriptors and the environment with it. `OSError` is the right shape,
        because every `connect()` call site already falls back to running the job in-process.
        """
        import importlib

        sock_path = tmp_path / 'dgsd' / 'sock'
        sock_path.parent.mkdir(parents=True)
        listener = __import__('socket').socket(__import__('socket').AF_UNIX,
                                               __import__('socket').SOCK_STREAM)
        listener.bind(str(sock_path))
        listener.listen(1)
        monkeypatch.setenv('DGS_RUNNER_SOCKET', str(sock_path))
        client = importlib.reload(importlib.import_module('tools.runner.client'))
        try:
            assert client.connect()                         # quiet: we own it
            elsewhere = os.getuid() + 1
            monkeypatch.setattr(os, 'getuid', lambda: elsewhere)
            with pytest.raises(OSError, match='not owned by us'):
                client.connect()
        finally:
            listener.close()
            importlib.reload(client)
