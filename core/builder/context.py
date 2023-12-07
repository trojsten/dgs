import abc
import copy
import pprint
import typing

import yaml
import logging
from pathlib import Path
from abc import ABCMeta, abstractmethod
from enschema import SchemaWrongKeyError, SchemaMissingKeyError, SchemaError, And
from typing import Any, Self

from enschema import Schema
from core.utilities import dicts, colour as c, crawler, logger

log = logger.setupLog('dgs')


class Context(metaclass=ABCMeta):
    defaults = {}                   # Defaults for every instance
    _schema: Schema = None  # Validation schema for the context, or None if it is not to be validated

    @property
    def schema(self) -> Schema:
        return self._schema

    @staticmethod
    def _default(name, func=None, dfl=''):
        if name is None:
            return dfl
        else:
            return name if func is None else func(name)

    def __init__(self, new_id=None, **defaults):
        self.id = new_id
        self.data = copy.deepcopy(self.defaults)
        self.add(defaults)

    def __str__(self):
        return f"<{self.__class__.__name__} named '{self.id}'>"

    def ident(self, *path: Any) -> tuple[Any]:
        """ Transform initialization parameters to identifier """
        return path

    def validate(self):
        if self._schema is None:
            log.warning(f"No validation schema defined for {self.__class__.__name__}, skipping validation")
        else:
            try:
                self._schema.validate(self.data)
            except (SchemaMissingKeyError, SchemaWrongKeyError, SchemaError) as exc:
                log.error(f"Failed to validate {c.name(self.__class__.__name__)} at {c.path(self.id)}")
                pprint.pprint(self.data)
                log.error("Against")
                pprint.pprint(self._schema.schema)
                raise exc

    def add(self, *dictionaries, overwrite=True):
        """ Merge a list of dictionaries into this context, overwriting existing keys """
        self.data = dicts.merge(self.data, *dictionaries, overwrite=overwrite)
        return self

    def absorb(self, *contexts: Self):
        """ Merge a list of other contexts into this context, overwriting existing keys """
        for ctx in contexts:
            self.data |= ctx.data
            if self._schema is not None:
                self._schema |= ctx.schema
        return self

    def adopt(self, key, ctx):
        """ Adopt a new child context `ctx` under the key `key` """
        assert isinstance(ctx, Context)
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)

        if self._schema is not None:
            # If child has no schema, accept anything, otherwise merge
            self._schema |= Schema(
                {key: {object: object} if ctx._schema is None else ctx._schema}
            )
        return self

    def override(self, key, ctx):
        self.data[key] = ctx
        return self

    def print(self):
        pprint.pprint(self.data, width=120)

    def add_number(self, number):
        return self.add({'number': number})

    def add_id(self, new_id):
        return self.add({'id': new_id})


class FileSystemContext(Context, metaclass=abc.ABCMeta):
    """
    Context that is reasonably mapped to a file system path, ideally inside a git repository.
    Typical traits are
        - can extract its structure from the directory tree
        - can load meta.yaml files with extra properties at all levels
        - has node_path that maps properties back to file system
    """
    _subcontext_key: str = None
    _subcontext_class: typing.ClassVar = None
    _validator_class: typing.ClassVar = None

    def __init__(self, root, *path, **defaults):
        super().__init__(self.name(self.ident(*path)), **defaults)
        self.root = root
        self.populate(*path)
        self.validate()

    @staticmethod
    def name(*path: Any) -> str:
        return '/'.join(*path)

    def validate_repo(self, *path: str) -> None:
        log.debug(f"Validating repository at {c.path(self.node_path(*path))}")
        root = self.node_path(*path)
        if self._validator_class is None:
            log.warning(f"No file system validator class defined for {c.name(self.__class__.__name__)}, skipping")
        else:
            try:
                self._validator_class(root).validate()
                log.info(f"File system structure at {c.path(root)} was successfully validated "
                         f"with {c.name(self._validator_class.__name__)}")
            except (SchemaError, SchemaMissingKeyError) as e:
                log.critical(f"File system structure at {c.path(root)} {c.err('failed')} to validate against "
                             f"{c.name(self._validator_class.__name__)}")
                raise e

    def load_yaml(self, *args):
        filename = Path(*args)
        log.debug(f"Loading {c.name(self.__class__.__name__)} metadata from {c.path(filename)}")
        try:
            contents = yaml.load(open(filename, 'r'), Loader=yaml.SafeLoader)
            contents = {} if contents is None else contents
        except FileNotFoundError as e:
            log.critical(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            raise e

        self.data = contents
        return self

    def load_meta(self, *path):
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
            self.__class__._schema.schema[key] = [self._subcontext_class._schema]

        return self

    def add_subdirs(self, *subcontext_args):
        log.debug(f"Adding subdirs to {self.__class__.__name__}: "
                     f"{self._subcontext_class.__name__} with args {subcontext_args}")
        cr = crawler.Crawler(self.node_path(*subcontext_args))
        self.add_list(self._subcontext_key,
                      [self._subcontext_class(self.root, *subcontext_args, child) for child in cr.subdirs()])


class BuildableContext(Context):
    """
    Only some contexts are meant to be built. This class provides a common ancestor.
    Currently only useful for sanity checks.
    """

    def __init__(self, root, *args, **kwargs):
        super().__init__(root)

    @abstractmethod
    def populate(self, *args, **kwargs):
        pass


class BuildableFilesystemContext(FileSystemContext, BuildableContext, metaclass=abc.ABCMeta):
    def __init__(self, root, *path, **defaults):
        super().__init__(root, *path, **defaults)
        # A filesystem context needs to validate its repository upon creation
        self.validate_repo(*path)


class ContextModule(Context):
    _schema = Schema({
        'id': And(str, len)
    })

    def __init__(self, module):
        super().__init__(module)
        self.populate()

    def populate(self):
        self.add_id(self.id)
