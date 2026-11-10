r"""
When a venue opens its envelopes, which is one instant and as many clocks as there are venues.

The volume records the instant in UTC and the venue records where it is; what a contestant
reads is the second applied to the first. Before this, every venue repeated the volume's local
time in its own meta -- 102 of the 117 said `start: 11:30` -- and the 15 that meant something
else by it were overwritten by `populate` before they reached a page, so `28/lisboa` printed
11:30 for the four years its meta said 10:30.

Nothing here needs a content repository: the conversion is a function and the schemas are
objects.
"""
import datetime

import pytest
from enschema import SchemaError

from core.utilities.schema import valid_timezone
from modules.naboj.builder.contexts.hierarchy import (
    ContextVenue,
    ContextVolume,
    local_minutes,
)

#: Volume 29, a November Friday: central Europe is on CET.
WINTER = datetime.date(2026, 11, 13)
#: `chem/02`, an April Friday: central Europe is on CEST, an hour further from UTC.
SUMMER = datetime.date(2024, 4, 12)
#: 10:30 UTC, which is 11:30 in Bratislava in winter -- volume 29's own start.
MORNING = 10 * 60 + 30


def at(hour, minute=0):
    return hour * 60 + minute


class TestTheZoneIsTheSystemsToKnow:
    def test_a_zone_this_competition_runs_in_is_valid(self):
        for zone in ('Europe/Bratislava', 'Europe/Prague', 'Europe/Budapest', 'Europe/Warsaw',
                     'Europe/Vienna', 'Europe/Madrid', 'Europe/Lisbon', 'Europe/Kyiv',
                     'Europe/Moscow'):
            assert valid_timezone(zone), zone

    def test_a_deprecated_link_is_still_a_zone(self):
        """`Europe/Uzhgorod` is a link to `Europe/Kyiv` and is still in the database."""
        assert valid_timezone('Europe/Uzhgorod')

    def test_something_that_is_not_a_zone_is_refused(self):
        assert not valid_timezone('Europe/Uzhhorod')     # the venue's spelling, not tz's
        assert not valid_timezone('Europe/Bratislava ')   # a stray space is not a zone either
        assert not valid_timezone('')

    def test_a_bare_abbreviation_is_a_zone_and_that_is_deliberate(self):
        """
        `CET` and `EET` really are in the database, as fixed-offset zones that never changed
        name. They are a poor thing to write in a meta -- `CET` does not follow a country that
        moves its clocks -- but refusing them would mean keeping a list of our own, which is
        the thing this validator exists not to do.
        """
        assert valid_timezone('CET')


class TestOneInstantManyClocks:
    """`local_minutes` is the whole of the new behaviour: UTC in, a wall clock out."""

    def test_the_organisers_own_clock(self):
        assert local_minutes(MORNING, WINTER, 'Europe/Bratislava') == at(11, 30)

    def test_a_venue_an_hour_behind(self):
        """Lisbon is on WET, so the same instant is an hour earlier on the wall."""
        assert local_minutes(MORNING, WINTER, 'Europe/Lisbon') == at(10, 30)

    def test_a_venue_an_hour_ahead(self):
        assert local_minutes(MORNING, WINTER, 'Europe/Kyiv') == at(12, 30)

    def test_summer_time_is_the_dates_business_not_the_zones(self):
        """
        The same zone, the same UTC, two answers -- which is why the volume's date is an
        argument. Read without it, every April volume would print an hour early.
        """
        assert local_minutes(MORNING, WINTER, 'Europe/Bratislava') == at(11, 30)
        assert local_minutes(MORNING, SUMMER, 'Europe/Bratislava') == at(12, 30)

    def test_moscow_is_converted_as_it_was_then(self):
        """
        Russia abolished winter time in 2011 and restored it in 2014, so Moscow was UTC+4 for
        volumes that do not exist and UTC+3 for the two that do. A table of offsets written
        once would have got one of these wrong.
        """
        assert local_minutes(MORNING, datetime.date(2013, 11, 16), 'Europe/Moscow') == at(14, 30)
        assert local_minutes(MORNING, datetime.date(2018, 11, 16), 'Europe/Moscow') == at(13, 30)

    def test_it_is_the_clock_and_not_the_day(self):
        """A conversion may cross midnight; what prints is a time, so only the clock returns."""
        assert local_minutes(at(23, 30), WINTER, 'Europe/Moscow') == at(2, 30)


class TestWhatAVenueMustSay:
    VENUE = {'id': 'lisboa-junior', 'code': 'PTLXJ', 'name': 'Lisboa', 'language': 'pt',
             'evaluators': 3, 'problems_modulo': [], 'timezone': 'Europe/Lisbon'}

    def test_a_venue_names_its_zone_and_need_not_name_a_start(self):
        ContextVenue._schema.validate(self.VENUE)

    def test_a_venue_may_still_override_the_start(self):
        ContextVenue._schema.validate(self.VENUE | {'start': at(9, 30)})

    def test_a_venue_without_a_zone_is_refused(self):
        with pytest.raises(SchemaError, match='timezone'):
            ContextVenue._schema.validate({k: v for k, v in self.VENUE.items()
                                           if k != 'timezone'})

    def test_a_zone_that_does_not_exist_is_refused(self):
        with pytest.raises(SchemaError):
            ContextVenue._schema.validate(self.VENUE | {'timezone': 'Europe/Uzhhorod'})

    def test_a_start_outside_the_day_is_refused(self):
        """1440 is midnight tomorrow, and `11:30` is 690 because YAML 1.1 reads sexagesimal."""
        with pytest.raises(SchemaError):
            ContextVenue._schema.validate(self.VENUE | {'start': 1440})


class TestWhatAVolumeMustSay:
    def test_the_volume_start_is_not_optional(self):
        """
        It is the one place the instant is written, so a volume without it has no time at all
        -- where a venue without one simply takes the volume's.
        """
        assert 'start' in {str(key) for key in ContextVolume._schema.schema}
