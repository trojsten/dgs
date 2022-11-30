from typing import Optional, Callable


def roman(number):
    if not type(number) == int:
        raise TypeError("Only integers between 1 and 3999 can be formatted as Roman numerals")

    if number <= 0 or number > 4000:
        raise ValueError("Argument must be between 1 and 3999")

    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = ""
    for i in range(len(ints)):
        count = int(number / ints[i])
        result += nums[i] * count
        number -= ints[i] * count
    return result


def check_digit(team: str, problem: int) -> int:
    return get_check_digit(f'{team}{problem:02d}')


def get_check_digit(data: str) -> int:
    try:
        digits = map(lambda x: int(x, 36), data)
    except ValueError as exc:
        raise ValueError("Found invalid character in barcode") from exc

    checksum = [d * w for d, w in zip(digits, itertools.cycle([7, 3, 1]))]
    return sum(checksum) % 10


def plural(how_many, one, two, many):
    if how_many == 1:
        return one
    if how_many > 2 and how_many < 5:
        return two
    else:
        return many


def isotex(date):
    return date.strftime('%Y--%m--%d')


def textbf(x: str) -> str:
    return rf"\textbf{{{x}}}"


def render_list(items, *, func: Optional[Callable]=None) -> str:
    if not isinstance(items, list):
        items = [items]

    if func is not None:
        items = list(map(func, items))

    for i, item in enumerate(items[:-2]):
        items[i] = f"{item},"

    if len(items) > 1:
        items[-2] = f"{items[-2]} a"

    return ' '.join(items)
