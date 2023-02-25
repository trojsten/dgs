from typing import Iterable
from schema import Schema, And

import core.utils.globals as glob


def string(x: str) -> bool:
    """ Is non-empty string """
    return And(str, len)


def valid_language(code: str) -> bool:
    return code in glob.languages.keys()


def merge(parent: Schema, *children: Iterable[Schema]) -> Schema:
    """ Merge an existing Schema with each in a list of child Schemas """
    for child in children:
        parent = merge_one(parent, child)
    return parent


def merge_one(parent: Schema, child: Schema, *, overwrite: bool = True) -> Schema:
    """
    Merge a child Schema into a parent Schema, optionally overwriting any existing keys.

    Parameters
    ----------
    parent : Schema
    child : Schema
    overwrite : bool
        Specifies whether existing keys should be overwritten or an exception should be raised

    Returns
    -------
    parent : Schema
    """
    if id(parent) == id(child):
        return parent

    if parent is None:
        return child

    for key in child._schema:
        if key in parent._schema:
            parent._schema[key] = Or(parent._schema[key], child._schema[key])
        else:
            parent._schema[key] = child._schema[key]

    return parent
