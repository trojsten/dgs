from enschema import And, Or, Regex

from core import i18n


def valid_language(code: str) -> bool:
    return code in i18n.languages.keys()


def valid_language_name(name: str) -> bool:
    return name in [lang.name for lang in i18n.languages.values()]
