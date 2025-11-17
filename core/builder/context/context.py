import abc
import copy
import logging
import pprint
import yaml

from typing import Any, Self, Optional
from pathlib import Path
from enschema import Schema, SchemaError

from core.utilities import colour as c

log = logging.getLogger('dgs')


class Context(abc.ABC):
    _defaults: dict[str, Any] = {}      # Defaults for every instance
    _schema: Optional[Schema] = None       # Validation schema for the context, or None if it is not to be validated
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
            contents = yaml.load(open(path, 'r'), Loader=yaml.SafeLoader)
            self._data = {} if contents is None else contents
        except FileNotFoundError as e:
            log.critical(c.err("[FATAL] Could not load YAML file"), c.path(path))
            raise e

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
                        "{c.name(self.__class__.__name__)}, skipping validation")
        else:
            try:
                self._data = self._schema.validate(self.data)
            except SchemaError as exc:
                log.error(f"{c.err('[FATAL] Failed to validate')} {c.name(self.__class__.__name__)} "
                          f"{c.path(self.id)}")
                pprint.pprint(self.data)
                log.error(f"against {self.__class__.__qualname__}")
                pprint.pprint(self.schema.schema)
                raise exc

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
