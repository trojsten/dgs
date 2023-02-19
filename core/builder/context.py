import math
import copy
import os
import pprint
import sys
import yaml
from typing import Iterable
from abc import ABCMeta, abstractmethod
from schema import Schema, SchemaWrongKeyError, SchemaMissingKeyError

import collections

from core.utils import dicts, colour as c, crawler, schema


class Context(metaclass=ABCMeta):
    defaults = {}       # Defaults for every instance
    schema = None       # Validation schema for the context, or None if it is not to be validated

    def __init__(self, root, *path, **defaults):
        self.id = None
        self.root = root
        self.data = copy.deepcopy(self.defaults)
        self.add(defaults)
        self.populate(*path)
        self.validate()

    def name(self, *path):
        self.id = '/'.join(map(str, path))

    def validate(self):
        if self.schema is None:
            print(f"{c.warn('WARNING')}: no schema defined for {self.__class__.__name__}, not validating")
        else:
            try:
                self.schema.validate(self.data)
            except SchemaMissingKeyError as exc:
                print(f"{c.err('ERROR')}: Failed to validate {c.name(self.__class__.__name__)} {c.path(self.id)}: {exc}")
                pprint.pprint(self.data)
                sys.exit(-1)

    def add(self, *dictionaries, overwrite=True):
        """ Merge a list of dictionaries into this context, overwriting existing keys """
        self.data = dicts.merge(self.data, *dictionaries, overwrite=overwrite)
        return self

    def absorb(self, *contexts, overwrite=True):
        """ Merge a list of other contexts into this context, overwriting existing keys """
        self.data = dicts.merge(self.data, *[ctx.data for ctx in contexts])
        self.schema = schema.merge(self.schema, *[ctx.schema for ctx in contexts])
        return self

    def adopt(self, key, ctx):
        """ Adopt a new child context `ctx` under the key `key` """
        assert isinstance(ctx, Context)
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)

        if self.schema is not None:
            self.schema._schema[key] = schema.merge_one(self.schema._schema.get(key), ctx.schema)
        return self

    def add_list(self, key, items):
        self.data[key] = [item.data for item in items]
        self.schema._schema[key] = [item.schema for item in items]
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
        """ Return node path for id tuple -- empty for base context """
        return ""

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


class BuildableContext(Context):
    """
    Only some contexts are meant to be built directly. This class provides a common ancestor.
    Not implemented yet.
    """
