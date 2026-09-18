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


#: A bare format kind -- `f` or `e` with no precision after the dot.
BareKind = re.compile(r'^[fe]$')


def natural(magnitude, kind: str) -> str:
    r"""
    A number formatted in `kind`'s notation to **its own** precision, not to Python's six.

    `f'{x:f}'` and `f'{x:e}'` do not mean "fixed" and "scientific"; they mean those with six
    decimal places, which is a precision nobody asked for. `\qty{102.000000}{\kilo\pascal}` is
    only ugly -- but `1e-8` formats as `0.000000`, so the value leaves the page altogether, and
    `24/venus`'s mass fraction is exactly that size. `g` escapes this because its precision
    counts significant digits rather than decimals, which is why `.eq` was never affected.

    `repr` gives the shortest string that reads back as the same float, so `Decimal(repr(x))` is
    exact and carries that precision and no more. Formatting it loses nothing, and the trailing
    zeros that remain are Python's padding rather than the number's own, so stripping them
    cannot drop a digit that was ever there.
    """
    import numbers as _numbers
    from decimal import Decimal
    if not isinstance(magnitude, _numbers.Number) or isinstance(magnitude, bool):
        return f'{magnitude:{kind}}'
    exact = Decimal(repr(float(magnitude)))
    if kind == 'f':
        printed = format(exact, 'f')
        return printed.rstrip('0').rstrip('.') if '.' in printed else printed
    mantissa, _, exponent = f'{magnitude:e}'.partition('e')
    if '.' in mantissa:
        mantissa = mantissa.rstrip('0').rstrip('.')
    return f'{mantissa}e{exponent}'
