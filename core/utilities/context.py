import math
import os
import pprint
import sys
import yaml

from collections.abc import Iterable

from core.utilities import dicts, colour as c


class Context:
    def __init__(self):
        self.data = {}

    def add(self, *dictionaries):
        """ Merge a list of dictionaries into this context, overriding same keys """
        self.data = dicts.merge(self.data, *dictionaries)
        return self

    def absorb(self, key, ctx):
        """ Absorb a new context `ctx` under the key `key` """
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)
        return self

    def load_yaml(self, *args):
        filename = os.path.join(*args)
        try:
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError:
            print(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            sys.exit(43)

        self.data = contents
        return self

    def load_meta(self, *args):
        return self.load_yaml(self.node_path(*args) / 'meta.yaml')

    def node_path(self, *args):
        raise NotImplementedError("Child classes must implement node_path method")

    def print(self):
        pprint.pprint(self.data)

    def set_number(self):
        return self.add({'number': self.number})

    def add_number(self, number):
        return self.add({'number': number})

    def set_id(self):
        return self.add({'id': self.id})

    def add_id(self, new_id):
        return self.add({'id': new_id})


def is_prime(what: int) -> int:
    if not type(what) is int or what < 2:
        return 0
    else:
        return int(all(what % x != 0 for x in range(2, math.isqrt(what) + 1)))


def split_mod(what: Iterable, count: int, first: int = 0) -> list:
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[(i + first) % count].append(item)
    return result


def split_div(what, count):
    return [] if what == [] else [what[0:count]] + split_div(what[count:], count)


def split_callback(what, callback, count):
    """
        Split `what` by `callback` function, using `count` bins
        what: [a]
        callback: a -> int, result must be 0 <= result < count
    """
    result = [[] for _ in range(0, count)]
    for i, item in enumerate(what):
        result[callback(i)].append(item)

    return result


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
