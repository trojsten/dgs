import zoneinfo

from core import i18n


def valid_language(code: str) -> bool:
    return code in i18n.languages


def valid_language_name(name: str) -> bool:
    return name in [lang.name for lang in i18n.languages.values()]


def valid_timezone(name: str) -> bool:
    """
    An IANA zone name, checked against the tz database.

    A list of our own would be a second answer to a question the database already answers, and
    would go stale the next time a country moves its clocks -- which is the whole reason the
    venue records a *zone* rather than an offset. `Europe/Kyiv` and `Europe/Uzhgorod` are both
    accepted because both are in it; the first is the canonical name and the second a link kept
    for compatibility, and nothing here needs to prefer one.

    **Which database is a dependency, not whatever the machine happens to ship**, and `tzdata` is
    in `pyproject.toml` for that reason alone. This used to read "the tz database this machine
    actually has", and the cost of that showed up when Debian 13 moved the backward-compatibility
    links into a separate `tzdata-legacy` package: `/usr/share/zoneinfo/CET` and
    `Europe/Uzhgorod` simply stopped existing, `available_timezones()` fell from 599 names to
    486, and a venue meta naming either would validate on one developer's machine and be refused
    on another's. None does today -- all 111 of them name a canonical zone -- so this was two
    failing tests rather than a broken build, which is the only reason it was cheap to find.
    """
    return name in zoneinfo.available_timezones()
