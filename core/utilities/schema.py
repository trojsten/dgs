from enschema import And, Or, Regex

import core.utilities.globals as glob


file = 'file'
link = 'link'
file_or_link = Or(file, link)


string = And(str, len)
commit_hash = Regex(r'[a-f0-9]+')


def valid_language(code: str) -> bool:
    return code in glob.languages.keys()