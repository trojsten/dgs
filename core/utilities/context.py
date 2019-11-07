import yaml
import os
import pprint
import argparse

from core.utilities import dicts, colour as c, argparser, jinja


class BaseBuilder():
    def __init__(self):
        self.create_argument_parser()
        self.parse_args()

        self.launch_directory = os.path.realpath(self.args.launch)
        self.template_root = os.path.realpath(self.args.template_root)
        self.output_directory = os.path.realpath(self.args.output) if self.args.output else None
        self.create_context()

    def print_debug_info(self):
        if self.args.debug:
            print("Launched {target} builder in {dir}".format(
                target=c.name(self.target),
                dir=c.path(self.args.launch),
            ))
            print(c.act("Content templates:"))
            pprint.pprint(self.templates)

            print(c.act("Context:"))
            self.context.print()

    def create_argument_parser(self):
        self.parser = argparse.ArgumentParser(description="Prepare a DGS input dataset from repository")
        self.parser.add_argument('launch', action=argparser.readable_dir)
        self.parser.add_argument('template_root', action=argparser.readable_dir)
        self.parser.add_argument('-o', '--output', action=argparser.writeable_dir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        return self.parser

    def parse_args(self):
        self.args = self.parser.parse_args()

    def id(self):
        raise NotImplementedError

    def path(self):
        raise NotImplementedError

    def print_build_info(self):
        print(
            c.act("Invoking"),
            c.name(self.module),
            c.act("template builder on"),
            c.name(self.target),
            c.path(os.path.join(*self.path())),
        )

    def create_context(self):
        self.context = self.root_context_class(os.path.realpath(self.args.launch), *self.id())

    def build(self):
        self.print_debug_info()
        self.print_build_info()

        for dir, templates in self.templates.items():
            for template in templates:
                jinja.print_template(os.path.join(self.template_root, dir), template, self.context.data, self.output_directory)

        print(c.ok("Template builder on"), c.name(self.target), c.ok("successful"))


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
        return self.load_YAML(self.nodePath(*args), 'meta.yaml')

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


def load_YAML(*args):
    try:
        result = yaml.load(open(os.path.join(*args), 'r'))
        if result is None:
            result = {}
    except FileNotFoundError as e:
        print(c.err("[FATAL] Could not load YAML file", c.path(e)))
        raise e
    return result


def load_meta(pathfinder, args):
    try:
        result = yaml.load(open(os.path.join(pathfinder(*args), 'meta.yaml'), 'r'))
        if result is None:
            result = {}
    except FileNotFoundError as e:
        print(c.err("[FATAL] Could not load metadata file)", c.path(e)))
        raise e
    return result


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
