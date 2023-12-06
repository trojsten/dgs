from enschema import And, Or, Regex

from core import i18n


file = 'file'
link = 'link'
file_or_link = Or(file, link)


string = And(str, len)
commit_hash = Regex(r'[a-f0-9]+')


def valid_language(code: str) -> bool:
    return code in i18n.languages.keys()


def valid_language_name(name: str) -> bool:
    return name in [lang.name for lang in i18n.languages.values()]
