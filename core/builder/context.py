import abc
import copy
import pprint
import yaml
import logging
from pathlib import Path
from abc import ABCMeta, abstractmethod
from schema import Schema, SchemaWrongKeyError, SchemaMissingKeyError, SchemaError, And
from typing import Any

from core.utilities import dicts, colour as c, crawler, schema as sch

logger = logging.getLogger(__name__)


class Context(metaclass=ABCMeta):
    defaults = {}       # Defaults for every instance
    _schema = None      # Validation schema for the context, or None if it is not to be validated

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

    def ident(self, *path: Any) -> tuple[Any]:
        """ Transform initialization parameters to identifier """
        return path

    def validate(self):
        if self._schema is None:
            logger.warning(f"No schema defined for {self.__class__.__name__}, skipping validation")
        else:
            try:
                self._schema.validate(self.data)
            except (SchemaMissingKeyError, SchemaWrongKeyError, SchemaError) as exc:
                logger.error(f"Failed to validate {c.name(self.__class__.__name__)} {c.path(self.id)}")
                pprint.pprint(self._schema)
                raise exc

    def add(self, *dictionaries, overwrite=True):
        """ Merge a list of dictionaries into this context, overwriting existing keys """
        self.data = dicts.merge(self.data, *dictionaries, overwrite=overwrite)
        return self

    def absorb(self, *contexts, conflict=sch.MergeFlags.OVERWRITE):
        """ Merge a list of other contexts into this context, overwriting existing keys """
        self.data = dicts.merge(self.data, *[ctx.data for ctx in contexts], overwrite=True)
        self._schema = sch.merge(self._schema, *[ctx._schema for ctx in contexts], conflict=conflict)
        return self

    def adopt(self, key, ctx):
        """ Adopt a new child context `ctx` under the key `key` """
        assert isinstance(ctx, Context)
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)

        if self._schema is not None:
            if ctx._schema is None:
                # If child has no schema, accept anything
                self._schema._schema[key] = {object: object}
            else:
                # otherwise merge schema (use the last one)
                self._schema._schema[key] = ctx._schema
        return self

    def print(self):
        pprint.pprint(self.data, width=120)

    def add_number(self, number):
        return self.add({'number': number})

    def add_id(self, new_id):
        return self.add({'id': new_id})


class FileSystemContext(Context, metaclass=abc.ABCMeta):
    """
    Context that is reasonably mapped to a repository path.
    Can load files, meta.yaml, has node_path
    """
    arg_schema = None
    _subcontext_key = None
    _subcontext_class = None
    _validator_class: None

    def __init__(self, root, *path, **defaults):
        if self.arg_schema is not None:
            Schema(self.arg_schema).validate(path)

        super().__init__(self.name(self.ident(*path)), **defaults)
        self.root = root
        self.populate(*path)
        self.validate()

    @staticmethod
    def name(*path: Any) -> str:
        return '/'.join(*path)

    def validate_repo(self, *path: str) -> None:
        root = self.node_path(*path)
        try:
            self._validator_class(root).validate()
            print(f"File system structure at {c.path(root)} was successfully validated "
                  f"with {c.name(self._validator_class.__name__)}")
        except SchemaError as e:
            print(f"File system structure at {c.path(root)} {c.err('failed')} to validate against "
                  f"{c.name(self._validator_class.__name__)}")
            raise e

    def load_yaml(self, *args):
        filename = Path(*args)
        try:
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError as e:
            logger.critical(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            raise e

        self.data = contents
        return self

    def load_meta(self, *path):
        logger.debug(f"Loading meta for {self.__class__.__name__} from {path}")
        return self.load_yaml(self.node_path(*path) / 'meta.yaml')

    @abstractmethod
    def node_path(self, *args):
        """ Return node path for id tuple -- empty for base context, must be implemented for children """

    @abstractmethod
    def populate(self, *path):
        """ Fill the context with data from the filesystem """

    def add_list(self, key, ctxs):
        self.data[key] = [item.data for item in ctxs]

        if self.__class__._schema is not None:
            self.__class__._schema._schema[key] = [self._subcontext_class._schema]

        return self

    def add_subdirs(self, *subcontext_args):
        logger.debug(f"Adding subdirs to {self.__class__.__name__}: "
                     f"{self._subcontext_class.__name__} with args {subcontext_args}")
        cr = crawler.Crawler(self.node_path(*subcontext_args))
        self.add_list(self._subcontext_key,
                      [self._subcontext_class(self.root, *subcontext_args, child) for child in cr.subdirs()])


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
