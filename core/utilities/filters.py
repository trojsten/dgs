from enschema import Schema, Or
from typing import Any, Callable, Union, List, Dict


def roman(number: int) -> str:
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


def isotex(date):
    return date.strftime('%Y--%m--%d')


def textit(x: str) -> str:
    return rf"\textit{{{x}}}"


def textbf(x: str) -> str:
    return rf"\textbf{{{x}}}"


def wrap(x: str, format_str: str) -> str:
    return format_str.format(x)


def identity(x: Any) -> Any:
    return x


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


def nth(x: int) -> str:
    return f"{x}{_nth(x)}"


def upnth(x: int) -> str:
    return rf"${x}^{{\mathrm{{{_nth(x)}}}}}$"


def render_list(items: Union[list, Any], *, func: Callable = identity, and_word: str = 'a') -> str:
    if not isinstance(items, list):
        items = [items]

    items = list(map(func, items))

    for i, item in enumerate(items[:-2]):
        items[i] = f"{item},"

    if len(items) > 1:
        items[-2] = f"{items[-2]} {and_word}"

    return ' '.join(items)


def process_people(people: Union[List[Dict[str, str]], Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Pre-process people metadata:
        - if a dict, wrap it in a list
        - if a list, pass through
        - otherwise raise exception
    """
    Schema(Or([Or(str, {'name': str, 'gender': str})], Or(str, {'name': str, 'gender': str}), str)).validate(people)
    if isinstance(people, str):
        return [dict(name=people, gender='?')]
    if isinstance(people, dict):
        return [people]
    elif isinstance(people, list):
        return [dict(name=person, gender='?') if isinstance(person, str) else person for person in people]
    else:
        raise TypeError(f"Invalid people type: {type(people)}")


def format_gender_suffix(people: dict[str, dict[str, str]], *, func: Callable = identity) -> str:
    """
    Format people metadata:
        -   if it is a dict, it should have name and gender, display that
        -   if it is a list of dicts, use plural and display a list of names

    Returns
    -------
    str : gender suffix
    """
    people = process_people(people)
    if len(people) > 1:
        return "i"
    else:
        if people[0]['gender'] == 'm':
            return ""
        elif people[0]['gender'] == 'f':
            return "a"
        elif people[0]['gender'] == 'n':
            return "o"
        elif people[0]['gender'] == '?':
            return r"\errorMessage{?}"
        else:
            raise ValueError(f"Tried to use an undefined gender suffix '{people[0]['gender']}'. "
                             f"Define 'gender' key in meta.yaml")


def format_people(people: Union[list, dict], *, func: Callable = identity, and_word: str = 'a') -> str:
    """
    Fully format a list of people
    Parameters
    ----------
    """

    people = process_people(people)
    return render_list([person['name'] if person['name'] != '' else r"\errorMessage{?}" for person in people],
                       func=func, and_word=and_word)


def num(x: float, precision: int):
    return rf"\num{{{x:.{precision}f}}}"


def float(x: float, precision: int):
    return rf"{x:.{precision}f}"


def exp(x: float, precision: int):
    return rf"{x:.{precision}g}"
