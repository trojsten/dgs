"""
The Containerfile's copies of things that live elsewhere.

Two facts in it are duplicates by necessity, and a duplicate nothing checks is one that goes
stale. Both failures would be quiet: a drifted FontPro pin builds *a* MinionPro, just not the one
the repository says; a `.containerignore` that lost an entry ships 650 MB of private sources into
an image without complaining.
"""
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTAINERFILE = ROOT / 'Containerfile'


@pytest.fixture(scope='module')
def containerfile():
    if not CONTAINERFILE.is_file():
        pytest.skip('no Containerfile')
    return CONTAINERFILE.read_text()


class TestTheFontProPinDoesNotDrift:
    """
    `.containerignore` excludes `.git/`, so `git submodule update --init` cannot run inside a
    build and the commit has to be written into the Containerfile by hand. This is the check
    that keeps that copy honest -- the same shape as `test_audit.py`'s descriptor/module.mk
    mirror, and for the same reason.
    """

    def test_the_arg_is_a_full_commit(self, containerfile):
        match = re.search(r'^ARG FONTPRO_COMMIT=([0-9a-f]{40})\s*$', containerfile, re.M)
        assert match, 'Containerfile has no pinned 40-character FONTPRO_COMMIT'

    def test_it_matches_the_submodule(self, containerfile):
        # Skipped inside the image, where `.git/` is correctly absent -- `pytest -q` runs there
        # too, and this is how that looks.
        if not (ROOT / '.git').exists():
            pytest.skip('not a checkout; this is how it looks from inside the image')
        arg = re.search(r'^ARG FONTPRO_COMMIT=([0-9a-f]{40})\s*$', containerfile, re.M)
        assert arg
        gitlink = subprocess.run(['git', 'rev-parse', 'HEAD:assets/fonts/FontPro'],
                                 cwd=ROOT, capture_output=True, text=True)
        if gitlink.returncode:
            pytest.skip('assets/fonts/FontPro is not a gitlink here')
        assert arg.group(1) == gitlink.stdout.strip(), (
            'Containerfile pins a different FontPro than the submodule does')


@pytest.fixture(scope='module')
def ignored():
    path = ROOT / '.containerignore'
    if not path.is_file():
        pytest.skip('no .containerignore')
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith('#')]


class TestNothingPrivateReachesTheImage:
    @pytest.mark.parametrize('entry', ['source/', '.git/', '.venv/', 'assets/fonts/FontPro/'])
    def test_the_expensive_and_the_private_are_excluded(self, ignored, entry):
        """
        `source/` is the one that matters: 657 MB of separate, private repositories that the
        image must never carry. The other three are what make the context 38 MB instead of 1.1 GB.
        """
        assert entry in ignored, f'{entry} is missing from .containerignore'

    def test_the_build_still_gets_what_it_needs(self, ignored):
        """The mirror image: excluding too much is just as broken, and quieter."""
        needed = ['pyproject.toml', 'uv.lock', 'install-pandoc.sh', 'core', 'modules',
                  'tools', 'Makefile', 'assets/fonts/MinionPro']
        for path in needed:
            assert path not in ignored, f'{path} is needed by the build but excluded'


class TestTheImageChecksItself:
    def test_both_stages_assert_their_tiers(self, containerfile):
        """
        A build that cannot typeset must not produce a tagged image. The old Dockerfile put
        `|| true` on every FontPro step and pushed exactly that on every tag.
        """
        assert 'expect-tiers.py markdown tex\n' in containerfile
        assert 'expect-tiers.py markdown tex latex pdf' in containerfile

    def test_no_failure_is_swallowed(self, containerfile):
        """
        `|| true` is what made the previous image's font build invisible: it sat on all three
        FontPro steps, so a build that produced no MinionPro still reported success and was
        pushed. Comments are excluded because the Containerfile says the words in prose, to
        explain why they are not there.
        """
        offenders = [line.strip() for line in containerfile.splitlines()
                     if '|| true' in line and not line.lstrip().startswith('#')]
        assert not offenders, f'a failure is being swallowed: {offenders}'
