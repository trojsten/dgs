import itertools
from typing import Iterable, Callable, List, Dict, Any
from core.utilities import dicts


def add_numbers(items: List[Any], start: int=0) -> List[Dict]:
    assert type(items) == list

    result = []
    num = start
    for item in items:
        result.append({
            'number': num,
            'id': item,
        })
        num += 1
    return result


def numerate(items: Dict, start: int=0) -> List[Dict]:
    num = start
    for item in items:
        assert type(item) == dict
        dicts.merge(item, {
            'number': num
        })
        num += 1
    return items


def split_mod(what: Iterable, count: int, *, first: int=0) -> list:
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[(i - first) % count].append(item)
    return result


def split_div(what: Iterable[Any], size: int) -> List[List[Any]]:
    """ Split `what` into chunks of length `size`, last chunk might not be full """
    what = iter(what)
    return list(itertools.takewhile(bool, (list(itertools.islice(what, size)) for _ in itertools.repeat(None))))
#   return list(itertools.batched(what, size)    for Python >=3.12


def split_callback(what: Iterable, callback: Callable, count: int) -> List[List]:
    """
        Split `what` by `callback` function, using `count` bins
        what: [a]
        callback: a -> int, result must be 0 <= result < count
    """
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[callback(i)].append(item)

    return result
