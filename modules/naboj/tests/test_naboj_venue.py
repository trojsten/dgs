r"""
What a venue's context says about the venue, asserted against the real metas.

Here and not in `core/tests/` for the reason `test_naboj_page_layout.py` gives: it needs
`source/naboj/` checked out, and is skipped when it is not.
"""
import datetime
import pathlib

import pytest
import yaml

from modules.naboj.builder.contexts import BuildableContextVenue
from modules.naboj.builder.contexts.buildable import local_start

pytestmark = pytest.mark.skipif(not pathlib.Path('source/naboj').is_dir(),
                                reason='source/naboj is not checked out')

VOLUME = pathlib.Path('source/naboj/phys/29')
VENUES = sorted(path.parent.name for path in VOLUME.glob('venues/*/meta.yaml'))


def venue(name):
    return BuildableContextVenue(pathlib.Path('source/naboj'), 'phys', 29, name).data['venue']


class TestTheStartTime:
    @pytest.mark.parametrize('name', [v for v in VENUES if not v.startswith('lisboa')])
    def test_a_venue_that_gives_a_start_keeps_it(self, name):
        """ A venue that really starts at another moment says so, and the volume does not overrule it. """
        meta = yaml.safe_load((VOLUME / 'venues' / name / 'meta.yaml').read_text())
        assert venue(name)['start'] == meta['start']

    @pytest.mark.parametrize('name', ['lisboa-junior', 'lisboa-senior'])
    def test_a_venue_in_another_zone_starts_at_the_same_moment(self, name):
        """
        Lisboa starts when everyone else does, an hour behind on the clock. Its meta gives the
        zone and no start, so the instructions read 10:30 there and 11:30 everywhere else.
        """
        assert venue(name)['timezone'] == 'Europe/Lisbon'
        assert venue(name)['start'] == 10 * 60 + 30


class TestLocalStart:
    def test_the_same_zone_changes_nothing(self):
        assert local_start(datetime.date(2026, 11, 13), 690, 'Europe/Bratislava', 'Europe/Bratislava') == 690

    def test_the_date_decides_the_offset(self):
        """ Kyiv is an hour ahead of Bratislava all year, but only because both switch on one day. """
        assert local_start(datetime.date(2026, 11, 13), 690, 'Europe/Bratislava', 'Europe/Kyiv') == 750
        assert local_start(datetime.date(2026, 7, 1), 690, 'Europe/Bratislava', 'Europe/Lisbon') == 630

    def test_a_start_that_crosses_midnight_is_refused(self):
        with pytest.raises(ValueError, match='not on the competition'):
            local_start(datetime.date(2026, 11, 13), 30, 'Europe/Bratislava', 'Europe/Lisbon')
