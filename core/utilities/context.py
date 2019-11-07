import yaml
import os
import pprint
import argparse

from core.utilities import dicts, colour as c, argparser, jinja


class Context():
    def __init__(self):
        self.data = {}

    def add(self, *args):
        self.data = dicts.merge(self.data, *args)
        return self

    def absorb(self, key, ctx):
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)
        return self

    def load_YAML(self, *args):
        try:
            filename = os.path.join(*args)
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError as e:
            print(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            raise e

        self.data = contents
        return self

    def load_meta(self, *args):
        return self.load_YAML(self.node_path(*args), 'meta.yaml')

    def node_path(self, *args):
        raise NotImplementedError("Child classes must implement nodePath method")

    def print(self):
        pprint.pprint(self.data)

    def set_number(self):
        return self.add({'number': self.number})

    def add_number(self, number):
        return self.add({'number': number})

    def set_id(self):
        return self.add({'id': self.id})

    def add_id(self, id):
        return self.add({'id': id})


def is_node(path):
    return (os.path.isdir(path) and os.path.basename(os.path.normpath(path))[0] != '.')


def list_child_nodes(node):
    return list(filter(lambda child: is_node(os.path.join(node, child)), sorted(os.listdir(node))))


def split_mod(what, step, first=0):
    result = [[] for i in range(0, step)]
    for i, item in enumerate(what):
        result[(i + first) % step].append(item)
    return result


def split_div(what, step):
    return [] if what == [] else [what[0:step]] + split_div(what[step:], step)


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
