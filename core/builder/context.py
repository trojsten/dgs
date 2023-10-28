import math
import copy
import os
import pprint
import sys
import yaml
import logging
from pathlib import Path
from typing import Iterable
from abc import ABCMeta, abstractmethod
from schema import Schema, SchemaWrongKeyError, SchemaMissingKeyError, SchemaError, And, Or, Optional

from core.utilities import dicts, colour as c, crawler, schema

logger = logging.getLogger(__name__)


class Context(metaclass=ABCMeta):
    defaults = {}       # Defaults for every instance
    schema = None       # Validation schema for the context, or None if it is not to be validated

    @staticmethod
    def default(name, func=None, dfl=''):
        if name is None:
            return dfl
        else:
            return name if func is None else func(name)

    def __init__(self, new_id=None, **defaults):
        self.id = new_id
        self.data = copy.deepcopy(self.defaults)
        self.add(defaults)

    def ident(self, *path):
        """ Transform initialization parameters to identifier """
        return path

    def validate(self):
        if self.schema is None:
            logger.warn(f"No schema defined for {self.__class__.__name__}, skipping validation")
        else:
            try:
                self.schema.validate(self.data)
            except (SchemaMissingKeyError, SchemaError) as exc:
                logger.error(f"Failed to validate {c.name(self.__class__.__name__)} {c.path(self.id)}")
                self.print()
                logger.error("against schema")
                pprint.pprint(self.schema._schema)
                raise exc
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
            if ctx.schema is None:
                # If child has no schema, accept anything
                self.schema._schema[key] = {object: object}
            else:
                # otherwise merge schema (use the last one)
                self.schema._schema[key] = ctx.schema
        return self

    def add_list(self, key, ctxs):
        self.data[key] = [item.data for item in ctxs]

        if self.__class__.schema is not None:
            self.__class__.schema._schema[key] = [self.subcontext_class.schema]

        return self

    def print(self):
        pprint.pprint(self.data, width=120)

    def add_number(self, number):
        return self.add({'number': number})

    def add_id(self, id):
        return self.add({'id': id})


class FileSystemContext(Context):
    """
    Context that is reasonably well mapped to a repository path.
    Can load files, meta.yaml, has node_path
    """
    arg_schema = None

    def __init__(self, root, *path, **defaults):
        if self.arg_schema is not None:
            Schema(self.arg_schema).validate(path)

        super().__init__(self.name(self.ident(*path)), **defaults)
        self.root = root
        self.populate(*path)
        self.validate()

    def name(self, *path):
        return '/'.join(*path)

    def load_YAML(self, *args):
        try:
            filename = os.path.join(*args)
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError as e:
            logger.critical(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            raise e
            sys.exit(43)

        self.data = contents
        return self

    def load_meta(self, *path):
        logger.debug(f"Loading meta for {self.__class__.__name__} from {path}")
        return self.load_YAML(self.node_path(*path) / 'meta.yaml')

    @abstractmethod
    def node_path(self, *args):
        """ Return node path for id tuple -- empty for base context """

    @abstractmethod
    def populate(self, *path):
        """ Fill the context with data from the filesystem """

    def add_subdirs(self, *subcontext_args):
        logger.debug(f"Adding subdirs to {self.__class__.__name__}: {self.subcontext_class.__name__} with args {subcontext_args}")
        cr = crawler.Crawler(self.node_path(*subcontext_args))
        self.add_list(self.subcontext_key, [self.subcontext_class(self.root, *subcontext_args, child) for child in cr.subdirs()])


class BuildableContext(Context):
    """
    Only some contexts are meant to be built directly. This class provides a common ancestor.
    Currently only useful for sanity checks.
    """


class ContextModule(Context):
    schema = Schema({'id': And(str, len)})

    def __init__(self, module):
        super().__init__(module)
        self.populate()

    def populate(self):
        self.add_id(self.id)
