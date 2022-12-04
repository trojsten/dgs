import itertools
from typing import Iterable, Callable, List, Dict, Any

from core.utils import dicts


def add_numbers(items: List[Any], numbers: Iterable=itertools.count()) -> List[Dict]:
    """
    Take a list `items` and return a list of dictionaries with number included.

    Parameters
    ----------
    items : List[Any]
        List of items to process
    numbers : Iterable
        An Iterable that produces the numbers, by default 0, 1, ...

    Returns
    -------
    List[Dict]
        A list of dictionaries in format {'number': int, 'id': item}
    """
    assert type(items) == list

    result = []
    for item in items:
        result.append({
            'number': next(numbers),
            'id': item,
        })
    return result


def numerate(items: Dict, numbers: Iterable=itertools.count()) -> List[Dict]:
    for item in items:
        assert type(item) == dict
        dicts.merge(item, {
            'number': next(numbers)
        })
    return items


def split_mod(what: Iterable, count: int, *, first: int=0) -> list:
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[(i + first) % count].append(item)
    return result


def split_div(what: Iterable[Any], size: int) -> List[List[Any]]:
    """
    Split `what` into chunks of length `size`. Last chunk might not be full. """
    what = iter(what)
    return list(itertools.takewhile(bool, (list(itertools.islice(what, size)) for _ in itertools.repeat(None))))
#   return list(itertools.batched(what, size)    for Python >=3.12


def split_callback(what: Iterable, callback: Callable, count: int) -> List[List]:
    """
    Split `what` by `callback` function, using `count` bins
        what: [Any]
        callback: Any -> int, result must be 0 <= result < count
    """
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[callback(i)].append(item)

    return result
