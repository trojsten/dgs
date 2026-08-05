import abc
import copy
import logging
import pprint
from pathlib import Path
from typing import Any, Self

import yaml
from enschema import Regex, Schema, SchemaError

from core.utilities import colour as c

log = logging.getLogger('dgs')


ValidIdentifier = Regex(r'^[A-Za-z_][A-Za-z_0-9]*$')

#: The only names the rendering context holds itself, and therefore the only ones a `values:` or
#: `derived:` entry must not claim: `values` and `derived` are spread into the context, so whoever
#: is added last would win. `const` is *adopted* as a child context rather than spread, so only the
#: bare name is taken -- its subkeys are untouched, and a value named `g` coexists with `const.g`.
#: Note `values` and `derived` themselves are section names in the file, never context names, and
#: `id` lives only in the metadata context, so none of those three are reserved.
RESERVED_NAMES = frozenset({'const', 'eq'})


class DuplicateKeyError(Exception):
    """
    Raised when a YAML mapping defines the same key twice. PyYAML keeps the last value at the
    first key's position, which is invisible in a diff and changes evaluation order for anything
    ordered -- `derived:` in particular.
    """
    def __init__(self, path: Path, keys: list[str]):
        super().__init__(f"Duplicate keys in {path}: {', '.join(map(str, keys))}")
        self.path = path
        self.keys = keys


class UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that refuses duplicate keys instead of silently keeping the last one."""
    def construct_mapping(self, node, deep=False):
        seen, duplicates = set(), []
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        if duplicates:
            raise DuplicateKeyError(Path(getattr(node.start_mark, 'name', '<yaml>')), duplicates)
        return super().construct_mapping(node, deep)


class Context(abc.ABC):
    _defaults: dict[str, Any] = {}      # Defaults for every instance
    _schema: Schema | None = None       # Validation schema for the context, or None if it is not to be validated
    _id: str = None
    _data: dict[str, Any] = None

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def data(self) -> dict:
        return self._data

    @property
    def id(self) -> str:
        return self._id

    @staticmethod
    def _default(name, func=None, dfl=''):
        if name is None:
            return dfl
        else:
            return name if func is None else func(name)

    def __init__(self, new_id=None, **defaults):
        self._id = new_id
        self._data = copy.deepcopy(self._defaults)

        if defaults is not None:
            self.add(**defaults)

    def __str__(self):
        return f"<{self.__class__.__name__} named '{self.id}'>"

    def load_yaml(self, path: Path):
        """
        Load context metadata from a YAML file. Replace with an empty dictionary if empty.
        """
        log.debug(f"Loading {c.name(self.__class__.__name__)} metadata from {c.path(path)}")
        try:
            with open(path, 'r') as f:
                contents = yaml.load(f, Loader=UniqueKeyLoader)
            self._data = {} if contents is None else contents
        except FileNotFoundError:
            log.critical(c.err(f"[FATAL] Could not load YAML file {c.path(path)}"))
            raise

        return self

    def ident(self, *path: Any) -> tuple[Any, ...]:
        """
        Transform initialization parameters to identifier. By default, this is just the same tuple.
        """
        return path

    def validate(self) -> None:
        """
        Validate the data against the schema, if provided
        """
        if self._schema is None:
            log.warning(f"No validation schema defined for class "
                        f"{c.name(self.__class__.__name__)}, skipping validation")
        else:
            try:
                self._data = self._schema.validate(self.data)
                log.debug(f"Context {c.name(self.__class__.__name__)} was {c.ok('validated')}")
            except SchemaError:
                log.error(f"{c.err('[FATAL] Failed to validate')} {c.name(self.__class__.__name__)} "
                          f"{c.path(self.id)}")
                pprint.pprint(self.data)
                log.error(f"against {self.__class__.__qualname__}")
                pprint.pprint(self.schema.schema)
                raise

    def add(self, **kwargs):
        """
        Merge extra key-value pairs into this context, overwriting existing keys.
        """
        self._data |= kwargs
        return self

    def adopt(self, **ctxs: 'Context') -> Self:
        """
        Adopt new child contexts `ctxs` from a dictionary of child contexts.
        """
        for key, ctx in ctxs.items():
            assert isinstance(ctx, Context)

            if key in self.data:
                self.data[key] |= ctx.data
            else:
                self.data[key] = copy.deepcopy(ctx.data)

            if self._schema is not None:
                # If child has no schema, accept anything, otherwise merge
                self._schema |= Schema(
                    {key: {object: object} if ctx._schema is None else ctx._schema}
                )
        return self

    def override(self, key, new_value):
        self.data[key] = new_value
        return self

    def print(self):
        pprint.pprint(self.data, width=120)

    def add_number(self, number):
        return self.add(number=number)

    def add_id(self, new_id):
        return self.add(id=new_id)

    def __eq__(self, other):
        return self.data == other.data and self.id == other.id

    def __ior__(self, other):
        if not isinstance(other, Context):
            return NotImplemented
        else:
            self._data |= other.data

            if self.schema is None or other.schema is None:
                self._schema = None
            else:
                self._schema |= other.schema

        return self

    def __or__(self, other):
        new = copy.deepcopy(self)
        new |= other
        return new
