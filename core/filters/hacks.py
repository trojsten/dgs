import regex as re


NumberWithExtraOne = re.compile(r'1\.?e[+-]?[0-9]+')


def cut_extra_one(num: str) -> str:
    """
    A helper function to remove extra leading "1" from numbers in scientific notation.
    "1e15" becomes "e15" so that `siunitx` does not render it as 1 · 10^15, but just 10^15.
    """
    if NumberWithExtraOne.match(num):
        return num[1:]
    else:
        return num
