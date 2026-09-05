"""
Filters for work with numbers. Feel free to extend.
"""
import numbers

from core.builder.context.quantities import PhysicsQuantity, QuantityList, QuantityProduct, QuantityRange

from .hacks import cut_extra_one


def roman(number: int) -> str:
    """ Render a number in Roman numerals """
    if not type(number) == int:
        raise TypeError("Only integers between 1 and 3999 can be formatted as Roman numerals")

    if number <= 0 or number >= 4000:
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
    if 2 <= how_many < 5:
        return two
    else:
        return many


def _nth(x: int) -> str:
    assert isinstance(x, int) and x >= 0
    if 10 <= x % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(x % 10, "th")


def nth(x: int) -> str:
    return f"{x}{_nth(x)}"


def format_float(x: float, precision: int | None = None):
    if precision is None:
        fmt = 'f'
    else:
        fmt = rf'.{precision}f'

    if isinstance(x, numbers.Number):
        printed = rf"{x:{fmt}}"
    elif isinstance(x, (PhysicsQuantity, QuantityRange, QuantityList, QuantityProduct)):
        printed = x.__format__(fmt)
    else:
        raise TypeError(f"Cannot handle type {type(x)} ({x})")

    return cut_extra_one(printed)

def format_general(x: float, precision: int | None = None):
    """
    Format a float in the exponential form
    """
    if precision is None:
        fmt = r'g'
    else:
        fmt = rf'.{precision}g'

    if isinstance(x, numbers.Number):
        printed = rf"{x:{fmt}}"
    elif isinstance(x, (PhysicsQuantity, QuantityRange, QuantityList, QuantityProduct)):
        printed = x.__format__(fmt)
    else:
        raise TypeError(f"Cannot handle type {type(x)} ({x})")

    return cut_extra_one(printed)


def format_exponential(x: float, precision: int | None = None):
    r"""
    Format a float in scientific notation, always.

    `format_general` is Python's `g`, which only reaches for an exponent below `1e-5`, so
    `1.004e-4` comes back as `0.0001004`. `24/venus` answers a mass fraction of exactly that
    size and the booklet prints it as a power of ten, hence a family of its own rather than a
    precision argument to `g`.

    The precision counts *decimals after the point*, as Python's `e` does, not significant
    figures as `g` does: `|e3` of `1.00356e-4` is `1.004e-04`.

    The exponent carries Python's two digits -- `1.004e-04`, not `1.004e-4`. siunitx sets the
    two identically, so the difference only ever shows in the source.
    """
    if precision is None:
        fmt = r'e'
    else:
        fmt = rf'.{precision}e'

    if isinstance(x, numbers.Number):
        printed = rf"{x:{fmt}}"
    elif isinstance(x, (PhysicsQuantity, QuantityRange, QuantityList, QuantityProduct)):
        printed = x.__format__(fmt)
    else:
        raise TypeError(f"Cannot handle type {type(x)} ({x})")

    return cut_extra_one(printed)

