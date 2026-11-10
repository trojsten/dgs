import zoneinfo

from core import i18n


def valid_language(code: str) -> bool:
    return code in i18n.languages


def valid_language_name(name: str) -> bool:
    return name in [lang.name for lang in i18n.languages.values()]


def valid_timezone(name: str) -> bool:
    """
    An IANA zone name, checked against the tz database this machine actually has.

    A list of our own would be a second answer to a question the system already answers, and
    would go stale the next time a country moves its clocks -- which is the whole reason the
    venue records a *zone* rather than an offset. `Europe/Kyiv` and `Europe/Uzhgorod` are both
    accepted because both are in the database; the first is the canonical name and the second a
    link kept for compatibility, and nothing here needs to prefer one.
    """
    return name in zoneinfo.available_timezones()
