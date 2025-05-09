import logging

from abc import ABC, abstractmethod
from typing import Any, ClassVar
from enschema import SchemaError, SchemaMissingKeyError

from core.utilities import colour as c, crawler

from .context import Context

log = logging.getLogger('dgs')


class FileSystemTreeContext(Context, ABC):
    """
    Context that is reasonably mapped to a file system tree, ideally inside a git repository.
    The directory tree is considered to be mappable to a `FileSystemContext`
    if the root contains a `meta.yaml` file, and the same applies to subdirectories.
    If a subdirectory is a node, this class will attempt to instantiate a `subcontext_class`
    Context for every directory and add them to itself under the key `subcontext_key`.

    Subdirectories that do not contain `meta.yaml` are ignored, but may be loaded
    by custom children classes instead.
    """
    _subcontext_key: str = 'subcontext'
    _subcontext_class: ClassVar = None
    _validator_class: ClassVar = None

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


    def load_meta(self, *path):
        """ Shorthand for loading the node_path meta.yaml file """
        return self.load_yaml(self.node_path(*path) / 'meta.yaml')

    @abstractmethod
    def node_path(self, *args):
        """ Return node path for the ident tuple -- empty for base context, must be implemented for children """

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
