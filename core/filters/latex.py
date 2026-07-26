
from collections.abc import Callable
from typing import Any

from enschema import Or, Schema

from core.builder.context.quantities import PhysicsQuantity

from ..builder.context.quantities.math import MathObject
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


def render_list(items: list | Any,
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


def process_people(people: list[dict[str, str]] | dict[str, str]) -> list[dict[str, str]]:
    """
    Pre-process people metadata:
        - if a dict, wrap it in a list
        - if a list, pass through
        - otherwise raise exception
    """
    Schema(Or([Or(str, {'name': str, 'gender': str})], Or(str, {'name': str, 'gender': str}), str)).validate(people)
    if isinstance(people, str):
        return [{'name': people, 'gender': '?'}]
    if isinstance(people, dict):
        return [people]
    elif isinstance(people, list):
        return [{'name': person, 'gender': '?'} if isinstance(person, str) else person for person in people]
    else:
        raise TypeError(f"Invalid people type: {type(people)}")


def format_gender_suffix(people: dict[str, dict[str, str]], *, func: Callable = identity) -> str:
    """
    Format people metadata:
        - if it is a dict, it should have name and gender, display that
        - if it is a list of dicts, use plural and display a list of names

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


def format_people(people: str | list | dict, *, func: Callable = identity, and_word: str = 'a') -> str:
    """
    Fully format a list of people
    Parameters
    ----------
    """

    people = process_people(people)
    return render_list([person['name'] if person['name'] != '' else r"\errorMessage{?}" for person in people],
                       func=func, and_word=and_word)


def num(x: float):
    """ Format as a `siunitx` \num{} input (as is)"""
    return rf'\num{{{x}}}'


def num_float(x: float, precision: int | None = None):
    """ Format as a `siunitx` \num{} input (float)"""
    return rf'\num{{{format_float(x, precision)}}}'


def num_general(x: float, precision: int | None = None):
    """ Format as a `siunitx` \num{} input (general)"""
    return rf'\num{{{format_general(x, precision)}}}'


def equals_float(q: PhysicsQuantity, precision: int | None = None):
    return q.equals_float(precision)


def equals_general(q: PhysicsQuantity, precision: int | None = None):
    return q.equals_general(precision)


def math_inline(math: MathObject) -> str:
    """
    Display as inline math. No punctuation argument: write any sentence
    punctuation outside the math, e.g. `(* eq | inline *).`
    """
    return f"{math}"


def math_display(math: MathObject, punct: str = '') -> str:
    """
    Display as block math with a label, optionally with trailing punctuation.

    Usage in templates:
        (* eq | disp *)          →  $$\\n    a + b\\n$$ {#eq:id}
        (* eq | disp(',') *)     →  $$\\n    a + b,\\n$$ {#eq:id}
    """
    return f"{math:disp{punct}}"


def math_aligned(math: MathObject, punct: str = '') -> str:
    r"""
    Display inside an \aligned{} environment with a label, optionally with
    trailing punctuation.

    Usage in templates:
        (* eq | align *)         →  $${\n    a &= b\n}$$ {#eq:id}
        (* eq | align('.') *)    →  $${\n    a &= b.\n}$$ {#eq:id}
    """
    return f"{math:align{punct}}"
