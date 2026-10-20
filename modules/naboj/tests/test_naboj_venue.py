r"""
What a venue's context says about the venue, asserted against the real metas.

Here and not in `core/tests/` for the reason `test_naboj_page_layout.py` gives: it needs
`source/naboj/` checked out, and is skipped when it is not.
"""
import pathlib

import pytest
import yaml

from modules.naboj.builder.contexts import BuildableContextVenue

pytestmark = pytest.mark.skipif(not pathlib.Path('source/naboj').is_dir(),
                                reason='source/naboj is not checked out')

VOLUME = pathlib.Path('source/naboj/phys/29')
VENUES = sorted(path.parent.name for path in VOLUME.glob('venues/*/meta.yaml'))


class TestTheStartTime:
    @pytest.mark.parametrize('venue', VENUES)
    def test_a_venue_starts_when_its_meta_says(self, venue):
        """
        The instructions print `venue.start`, and a venue in another time zone starts at another
        local time. It used to be overwritten with the volume's start unconditionally, so Lisboa,
        an hour behind the rest, was told to open its envelopes at 11:30 instead of 10:30.
        """
        meta = yaml.safe_load((VOLUME / 'venues' / venue / 'meta.yaml').read_text())
        context = BuildableContextVenue(pathlib.Path('source/naboj'), 'phys', 29, venue)
        assert context.data['venue']['start'] == meta['start']
