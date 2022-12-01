import math
import copy
import os
import pprint
import sys
import yaml

from collections.abc import Iterable

from core.utilities import dicts, colour as c, crawler


class Context():
    defaults = {}

    def __init__(self, **defaults):
        self.data = copy.deepcopy(self.defaults)
        self.add(defaults)

    def add(self, *dictionaries):
        """ Merge a list of dictionaries with into this context, overriding same keys """
        self.data = dicts.merge(self.data, *dictionaries)
        return self

    def absorb(self, *ctxs):
        self.data = dicts.merge(self.data, *[ctx.data for ctx in ctxs])
        return self

    def adopt(self, key, ctx):
        """ Adopt a new child context `ctx` under the key `key` """
        assert isinstance(ctx, Context)
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)
        return self

    def load_YAML(self, *args):
        try:
            filename = os.path.join(*args)
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError as e:
            print(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            sys.exit(43)

        self.data = contents
        return self

    def load_meta(self, *args):
        return self.load_YAML(self.node_path(*args) / 'meta.yaml')

    def node_path(self, *args):
        raise NotImplementedError("Child classes must implement node_path method")

    def print(self):
        pprint.pprint(self.data)

    def add_number(self, number):
        return self.add({'number': number})

    def add_id(self, id):
        return self.add({'id': id})

    def add_children(self, subcontext_class, subcontext_key, *subcontext_args):
        """ Use a Crawler to scan the filesystem and add children to this Context """
        cr = crawler.Crawler(self.node_path(*subcontext_args))
        self.add({subcontext_key: [subcontext_class(*subcontext_args, child).data for child in cr.children()]})

    def add_subdirs(self, subcontext_class, subcontext_key, subcontext_args, root):
        cr = crawler.Crawler(self.node_path(*root))
        self.add({subcontext_key: [subcontext_class(*subcontext_args, child).data for child in cr.subdirs()]})
