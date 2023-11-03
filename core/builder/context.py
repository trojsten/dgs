import copy
import datetime
import os
import pprint
import yaml
import logging
from abc import ABCMeta, abstractmethod
from schema import Schema, SchemaMissingKeyError, SchemaError, And
from pathlib import Path

import core.utilities.schema as sch
from core.utilities import dicts, colour as c, crawler

logger = logging.getLogger(__name__)


class Context(metaclass=ABCMeta):
    _defaults = {}       # Defaults for every instance
    _schema = None       # Validation schema for the context, or None if it is not to be validated

    @staticmethod
    def default(name, func=None, dfl=''):
        if name is None:
            return dfl
        else:
            return name if func is None else func(name)

    def __init__(self, new_id=None, **defaults):
        self._id = new_id
        self._data = copy.deepcopy(self._defaults)
        self.add(defaults)

    @property
    def data(self):
        return self._data

    @property
    def schema(self):
        return self._schema

    @property
    def id(self):
        return self._id

    def ident(self, *path):
        """ Transform initialization parameters to identifier """
        return path

    def validate(self):
        if self._schema is None:
            logger.warning(f"No schema defined for {self.__class__.__name__}, skipping validation")
        else:
            try:
                self._schema.validate(self._data)
            except (SchemaMissingKeyError, SchemaError) as exc:
                logger.error(f"Failed to validate {c.name(self.__class__.__name__)} {c.path(self.id)}")
                self.print()
                logger.error("against schema")
                pprint.pprint(self._schema._schema, width=120)
                raise exc

    def add(self, *dictionaries, overwrite=True):
        """ Merge a list of dictionaries into this context, overwriting existing keys """
        self._data = dicts.merge(self._data, *dictionaries, overwrite=overwrite)
        return self

    def absorb(self, *contexts, overwrite=True):
        """ Merge a list of other contexts into this context, overwriting existing keys """
        self._data = dicts.merge(self._data, *[ctx._data for ctx in contexts], overwrite=overwrite)
        self._schema = sch.merge(self._schema, *[ctx._schema for ctx in contexts])
        return self

    def adopt(self, key, ctx):
        """ Adopt a new child context `ctx` under the key `key` """
        assert isinstance(ctx, Context)
        self._data[key] = dicts.merge(self._data.get(key), ctx._data)

        if self._schema is not None:
            if ctx._schema is None:
                # If child has no schema, accept anything
                self._schema._schema[key] = {object: object}
            else:
                # otherwise merge schema (use the last one)
                self._schema._schema[key] = ctx._schema
        return self

    def add_list(self, key, ctxs):
        self._data[key] = [item._data for item in ctxs]

        if self.__class__._schema is not None:
            self.__class__._schema._schema[key] = [self.subcontext_class._schema]

        return self

    def override(self, key, ctx):
        if key not in self._data:
            self._data[key] = ctx[key]

        return self

    def print(self):
        pprint.pprint(self._data, width=120)

    def add_number(self, number):
        return self.add({'number': number})

    def add_id(self, new_id):
        return self.add({'id': new_id})


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

    @staticmethod
    def name(*path):
        return '/'.join(*path)

    def load_yaml(self, *args):
        filename = os.path.join(*args)
        try:
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError as e:
            logger.critical(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            raise e

        self._data |= contents
        return self

    def load_meta(self, *path):
        logger.debug(f"Loading meta for {self.__class__.__name__} from {path}")
        return self.load_yaml(self.node_path(*path) / 'meta.yaml')

    @abstractmethod
    def node_path(self, *args):
        """ Return node path for id tuple -- empty for base context """

    @abstractmethod
    def populate(self, *path):
        """ Fill the context with data from the filesystem """

    def add_subdirs(self, *subcontext_args):
        logger.debug(f"Adding subdirs to {self.__class__.__name__}: {self.subcontext_class.__name__} "
                     f"with args {subcontext_args}")
        cr = crawler.Crawler(self.node_path(*subcontext_args))
        self.add_list(self.subcontext_key,
                      [self.subcontext_class(self.root, *subcontext_args, child) for child in cr.subdirs()])


class BuildableContext(Context):
    """
    Only some contexts are meant to be built directly. This class provides a common ancestor.
    Currently only useful for sanity checks.
    """
    _schema = Schema({
        'build': {
            'user': And(str, len),
            'dgs': {
                'hash': sch.commit_hash,
                'branch': str,
            },
            'repo': {
                'hash': sch.commit_hash,
                'branch': str,
            },
            'timestamp': datetime.datetime,
        }
    })

    def _add_build_info(self, repo_root: Path):
        # Add build metadata
        self.add({
            'build': {
                'user': os.environ.get('USERNAME'),
                'dgs': {
                    'hash': sch.get_last_commit_hash(),
                    'branch': sch.get_branch(),
                },
                'repo': {
                    'hash': sch.get_last_commit_hash(repo_root),
                    'branch': sch.get_branch(repo_root),
                },
                'timestamp': datetime.datetime.now(datetime.timezone.utc),
            }
        })


class ContextModule(Context):
    _schema = Schema({'id': And(str, len)})

    def __init__(self, module):
        super().__init__(module)
        self.populate()

    def populate(self):
        self.add_id(self._id)
