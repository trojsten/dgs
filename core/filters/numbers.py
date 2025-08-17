"""
Filters for work with numbers. Feel free to extend.
"""
import numbers

from core.builder.context import PhysicsConstant
from .hacks import cut_extra_one



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
    if isinstance(x, numbers.Number):
        if precision is None:
            return rf"{x:f}"
        else:
            return rf"{x:.{precision}f}"
    elif isinstance(x, PhysicsConstant):
        return x.fullf(precision)
    else:
        raise TypeError(f"Cannot handle type {x}")


def format_general(x: float, precision: int = None):
    """
    Format a float in the exponential form
    """
    if isinstance(x, numbers.Number):
        if precision is None:
            printed = rf"{x:g}"
        else:
            printed = rf"{x:.{precision}g}"
    elif isinstance(x, PhysicsConstant):
        printed = x.fullg(precision)
    else:
        raise TypeError(f"Cannot handle type {x}")

    return cut_extra_one(printed)
