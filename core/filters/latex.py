
from collections.abc import Callable
from typing import Any

from enschema import Or, Schema

from core.builder.context.quantities import (PhysicsQuantity, QuantityList, QuantityProduct,
                                             QuantityRange)

from ..builder.context.quantities.math import MathObject
from .numbers import _nth, format_exponential, format_float, format_general


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


#: Types that format themselves as a complete siunitx call -- `\num{…}` when dimensionless,
#: `\qty{…}{…}` otherwise, and `\qtyrange`, `\qtylist`, `\qtyproduct` for the collections.
#: `format_float` and `format_general` delegate to their `__format__`, so what comes back is
#: already a call and must not be wrapped in another one.
_SELF_FORMATTING = (PhysicsQuantity, QuantityRange, QuantityList, QuantityProduct)


def num(x: float):
    r"""
    Format as a `siunitx` \num{} input (as is).

    Idempotent: a quantity already renders as `\num{…}` or `\qty{…}{…}`, and wrapping that gives
    `\num{\num{0.0072}}`, which siunitx cannot parse. `28/enrichment` is how this surfaced -- the
    obvious way to write it hands a dimensionless quantity straight to `|ng`.
    """
    return f'{x}' if isinstance(x, _SELF_FORMATTING) else rf'\num{{{x}}}'


def num_float(x: float, precision: int | None = None):
    r""" Format as a `siunitx` \num{} input (float). Idempotent, see `num`. """
    printed = format_float(x, precision)
    return printed if isinstance(x, _SELF_FORMATTING) else rf'\num{{{printed}}}'


def num_general(x: float, precision: int | None = None):
    r""" Format as a `siunitx` \num{} input (general). Idempotent, see `num`. """
    printed = format_general(x, precision)
    return printed if isinstance(x, _SELF_FORMATTING) else rf'\num{{{printed}}}'


def num_exponential(x: float, precision: int | None = None):
    r""" Format as a `siunitx` \num{} input (scientific notation). Idempotent, see `num`. """
    printed = format_exponential(x, precision)
    return printed if isinstance(x, _SELF_FORMATTING) else rf'\num{{{printed}}}'


def equals_float(q: PhysicsQuantity, precision: int | None = None):
    return q.equals_float(precision)


def equals_general(q: PhysicsQuantity, precision: int | None = None):
    return q.equals_general(precision)


def equals_exponential(q: PhysicsQuantity, precision: int | None = None):
    return q.equals_exponential(precision)


def approx_float(q: PhysicsQuantity, precision: int | None = None):
    return q.approx_float(precision)


def approx_general(q: PhysicsQuantity, precision: int | None = None):
    return q.approx_general(precision)


def approx_exponential(q: PhysicsQuantity, precision: int | None = None):
    return q.approx_exponential(precision)


def quad_text(word: str) -> str:
    """
    A translated word set as text inside maths, with a `\\quad` either side.

    `core/latex/math.tex` defines `\\QText{w}` as `\\quad\\text{w}\\quad`, which is how a
    conjunction is joined to the equations on either side of it. Written as a filter so the
    source says `(§ i18n.andw|q §)` rather than spelling the macro out around a lookup.
    """
    return rf"\QText{{{word}}}"


def quad_quad_text(word: str) -> str:
    """
    The same with `\\qquad`, from `\\QQText`. The wider of the two, and the one to reach for
    when the word joins two whole equations rather than two terms.
    """
    return rf"\QQText{{{word}}}"


def math_raw(math: MathObject) -> str:
    """
    The fragment with no delimiters at all, for building a larger expression from a named piece.

    This is what a bare `(§ eq.foo §)` does, so the filter exists mainly to be explicit.
    """
    return f"{math}"


def math_inline(math: MathObject) -> str:
    """
    Render as inline math. No punctuation argument: write any sentence
    punctuation outside the math, e.g. `(§ eq.foo|inl §).`
    """
    return f"{math:inl}"


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
