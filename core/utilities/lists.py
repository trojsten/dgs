from typing import Iterable, Callable, List
from core.utilities import dicts

def add_numbers(what, start=0):
    result = []
    num = start
    for item in what:
        result.append({
            'number': num,
            'id': item,
        })
        num += 1
    return result


def numerate(objects, start=0):
    num = start
    for item in objects:
        dicts.merge(item, {
            'number': num
        })
        num += 1
    return objects


def split_mod(what: Iterable, count: int, *, first: int=0) -> list:
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[(i - first) % count].append(item)
    return result


def split_div(what, count):
    return [] if what == [] else [what[0:count]] + split_div(what[count:], count)


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
