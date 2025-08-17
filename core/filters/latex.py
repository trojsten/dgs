from typing import Any, Union, Callable, Optional

from enschema import Schema, Or

from .numbers import _nth, format_float, format_general


def isotex(date):
    return date.strftime('%Y--%m--%d')


def textit(x: str) -> str:
    return rf"\textit{{{x}}}"


def textbf(x: str) -> str:
    return rf"\textbf{{{x}}}"


def wrap(x: str, format_str: str) -> str:
    return format_str.format(x)


def identity(x: Any) -> Any:
    """Identity helper function"""
    return x



def upnth(x: int) -> str:
    """
    Superscripted nth for LaTeX
    """
    return rf"${x}^{{\mathrm{{{_nth(x)}}}}}$"


def render_list(items: Union[list, Any],
                *,
                func: Callable = identity,
                and_word: str = 'a',
                oxford_comma: bool = False) -> str:
    """
    Render a list of items, optionally with a function `func` applied to every item, joined by spaces with commas.

    Parameters:
        `func`
            function to apply to every item
        `and_word`
            word to insert before the last item
        `oxford_comma`
            if True, insert a comma before the "and" word
    """
    if not isinstance(items, list):
        items = [items]

    items = list(map(func, items))

    for i, item in enumerate(items[:(-1 if oxford_comma else -2)]):
        items[i] = f"{item},"

    if len(items) > 1:
        items[-2] = f"{items[-2]} {and_word}"

    return ' '.join(items)


def process_people(people: Union[list[dict[str, str]], dict[str, str]]) -> list[dict[str, str]]:
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
        person = people[0]
        if person['gender'] == 'm':
            return ""
        elif person['gender'] == 'f':
            return "a"
        elif person['gender'] == 'n':
            return "o"
        elif person['gender'] == '?':
            return r"\errorMessage{?}"
        else:
            raise ValueError(f"Tried to use an undefined gender suffix '{person['gender']}'. "
                             f"Define 'gender' key in meta.yaml")


def format_people(people: Union[str, list, dict], *, func: Callable = identity, and_word: str = 'a') -> str:
    """
    Fully format a list of people
    Parameters
    ----------
    """

    people = process_people(people)
    return render_list([person['name'] if person['name'] != '' else r"\errorMessage{?}" for person in people],
                       func=func, and_word=and_word)


def num(x: float, precision: Optional[int] = None):
    """ Format as a `siunitx` \num{} input"""
    return rf'\num{{{format_float(x, precision)}}}'


def num_general(x: float, precision: Optional[int] = None):
    """ Format as a `siunitx` \num{} input"""
    return rf'\num{{{format_general(x, precision)}}}'
