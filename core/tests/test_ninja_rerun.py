r"""
Whether a document wants a second xelatex pass, decided from the first pass's own log.

Every document used to be compiled twice unconditionally, in both build systems, and xelatex is
71 % of the build -- 127 edges against 585 of 819 edge-seconds. A **cold** pass asks for a rerun
in every one of volume 29's document kinds and a **warm** pass asks in none, so this leaves a cold
build as it was and takes a pass off the authoring loop.

The quiet cases are the point. A matcher that fires on every log is not a bug anyone sees: the
build simply goes on doing what it always did, and the feature looks like it does not work.
"""
import pathlib

from tools.ninja.rerun import wanted

#: The four requests a real cold first pass emits here, one per line of a log.
REQUESTS = (
    'Package hyperref Warning: Rerun to get /PageLabels entry.',
    'LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.',
    '(rerunfilecheck)                Rerun to get outlines right',
    'Package lastpage Warning: Rerun to get the references right on input line 293.',
)

#: In every log, cold or warm, and the reason `Rerun` alone cannot be the matcher.
BANNER = ('Package: rerunfilecheck 2022-07-10 v1.10 Rerun checks for auxiliary files (HO)\n'
          'Package uniquecounter Info: New unique counter `rerunfilecheck\' on input line 285.\n')


def log(tmp_path: pathlib.Path, text: str) -> pathlib.Path:
    path = tmp_path / 'doc.log'
    path.write_text(text)
    return path


class TestARequestIsHeard:
    def test_each_of_the_four(self, tmp_path):
        for request in REQUESTS:
            assert wanted(log(tmp_path, f'{BANNER}\n{request}\nOutput written on doc.pdf\n')), \
                request


class TestTheQuietCases:
    def test_a_warm_log_asks_for_nothing(self, tmp_path):
        """
        What `rerunfilecheck` says once the `.out` has settled -- the shape of every warm log,
        and the one this exists to detect.
        """
        text = (f"{BANNER}\n"
                "Package rerunfilecheck Info: File `doc.out' has not changed.\n"
                '(rerunfilecheck)             Checksum: D41D8CD98F00B204E9800998ECF8427E;0.\n'
                'Output written on doc.pdf (44 pages).\n')
        assert not wanted(log(tmp_path, text))

    def test_the_banner_alone_is_not_a_request(self, tmp_path):
        """
        `Rerun checks for auxiliary files` carries a capital `Rerun` and is in every log, so a
        matcher of `Rerun` alone never skips a pass and the whole change silently does nothing.
        """
        assert not wanted(log(tmp_path, BANNER))

    def test_an_empty_log_asks_for_nothing(self, tmp_path):
        assert not wanted(log(tmp_path, ''))


class TestUnreadableMeansYes:
    """
    The two mistakes are not symmetrical. A wrong *skip* ships a booklet with a stale
    cross-reference in it; a wrong *rerun* costs two seconds.
    """

    def test_a_missing_log(self, tmp_path):
        assert wanted(tmp_path / 'absent.log')

    def test_a_directory_in_its_place(self, tmp_path):
        (tmp_path / 'doc.log').mkdir()
        assert wanted(tmp_path / 'doc.log')

    def test_undecodable_bytes_do_not_raise(self, tmp_path):
        """A log is whatever TeX wrote, including a font name in an unexpected encoding."""
        path = tmp_path / 'doc.log'
        path.write_bytes(b'\xff\xfe some bytes\nLaTeX Warning: Label(s) may have changed. '
                         b'Rerun to get cross-references right.\n')
        assert wanted(path)
