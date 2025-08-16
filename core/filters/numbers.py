"""
Filters for work with numbers. Feel free to extend.
"""

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


def roman(number: int) -> str:
    """ Render a number in Roman numerals """
    if not type(number) == int:
        raise TypeError("Only integers between 1 and 3999 can be formatted as Roman numerals")

    if number <= 0 or number > 4000:
        raise ValueError(f"Argument must be between 1 and 3999, got {number}")

    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = ""
    for i in range(len(ints)):
        count = int(number / ints[i])
        result += nums[i] * count
        number -= ints[i] * count
    return result


def plural(how_many, one, two, many):
    if how_many == 1:
        return one
    if 2 < how_many < 5:
        return two
    else:
        return many


def _nth(x: int) -> str:
    assert isinstance(x, int)
    assert x >= 0
    if x % 10 in [0, 4, 5, 6, 7, 8, 9]:
        return "th"
    else:
        if (x % 100) // 10 == 1:
            return "th"
        else:
            match x % 10:
                case 1:
                    return "st"
                case 2:
                    return "nd"
                case 3:
                    return "rd"
            return "th"


def nth(x: int) -> str:
    return f"{x}{_nth(x)}"


def format_float(x: float, precision: int = None):
    return rf"{x:.{precision}f}"


def format_general(x: float, precision: int = None):
    """
    Format a float in the exponential form
    """
    if precision is None:
        printed = rf"{x:g}"
    else:
        printed = rf"{x:.{precision}g}"

    return cut_extra_one(printed)
