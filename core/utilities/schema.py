import copy
import os
import schema

from typing import Self
from schema import And, Or, Regex
from enum import Enum

import core.utilities.globals as glob


file = 'file'
link = 'link'
file_or_link = Or(file, link)


string = And(str, len)
commit_hash = Regex(r'[a-f0-9]+')


class MergeFlags(Enum):
    """
    Conflict resolution algorithm for mergeing Schemas
    """
    KEEP = 0            # Keep parent values
    EXCEPTION = 1       # Raise an exception
    OVERWRITE = 2       # Keep child values
    FUSE = 3            # Recursively fuse children Schemas
    ALTERNATIVE = 4     # Replace with Or(self.schema[key], other.schema[key])


class Schema(schema.Schema):
    def _merge(self, other: Self, *, conflict: MergeFlags = MergeFlags.OVERWRITE):
        """
        Merge a child Schema into a parent Schema, optionally overwriting any existing keys.

        Parameters
        ----------
        other : Schema
        conflict : MergeFlags
            Specifies what to do if a key is found both in parent and child:
                IGNORE: keep the value of parent
                EXCEPTION: throw an exception
                OVERWRITE: keep the value of child, discarding the value of parent (default)
                FUSE: allow both values from parent's and child's schema
        """
        assert isinstance(other, Schema), "Can only merge a Schema with another Schema"
        for key in other.schema:
            if key in self.schema:
                match conflict:
                    case MergeFlags.KEEP:
                        pass
                    case MergeFlags.EXCEPTION:
                        raise schema.SchemaError(f"Key collision for {key}")
                    case MergeFlags.OVERWRITE:
                        self.schema[key] = other.schema[key]
                    case MergeFlags.FUSE:
                        self.schema[key] |= other.schema[key]
                    case MergeFlags.ALTERNATIVE:
                        self.schema[key] = Or(self.schema[key], other.schema[key])
            else:
                self.schema[key] = other.schema[key]
        return self

    def __or__(self, other: Self) -> Self:
        sch = copy.deepcopy(self)
        return sch._merge(other, conflict=MergeFlags.ALTERNATIVE)

    def __and__(self, other: Self) -> Self:
        sch = copy.deepcopy(self)
        return sch._merge(other, conflict=MergeFlags.OVERWRITE)

    def __add__(self, other) -> Self:
        sch = copy.deepcopy(self)
        return sch._merge(other, conflict=MergeFlags.FUSE)

    def __ior__(self, other: Self):
        return self._merge(other, conflict=MergeFlags.ALTERNATIVE)

    def __iand__(self, other: Self):
        return self._merge(other, conflict=MergeFlags.OVERWRITE)

    def __iadd__(self, other: Self):
        return self._merge(other, conflict=MergeFlags.FUSE)


def valid_language(code: str) -> bool:
    return code in glob.languages.keys()
