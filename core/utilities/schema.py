import os
import subprocess
import schema

from schema import Schema, And, Or, Regex
from enum import Enum

import core.utilities.globals as glob


file = 'file'
link = 'link'
file_or_link = Or(file, link)


string = And(str, len)
commit_hash = Regex(r'[a-f0-9]+')


class MergeFlags(Enum):
    IGNORE = 0
    EXCEPTION = 1
    OVERWRITE = 2
    FUSE = 3


def valid_language(code: str) -> bool:
    return code in glob.languages.keys()


def check_output(command, *, cwd) -> str:
    return subprocess.check_output(command, cwd=cwd if cwd is not None else os.getcwd()).decode().rstrip("\n")


def get_last_commit_hash(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--short", "--verify", "master"], cwd=cwd)


def get_branch(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--symbolic-full-name", "--abbrev-ref", "HEAD"], cwd=cwd)


def merge(parent: Schema, *children: Schema, conflict: MergeFlags = MergeFlags.OVERWRITE) -> Schema:
    """ Merge an existing Schema with each in a list of child Schemas """
    for child in children:
        parent = merge_one(parent, child, conflict=conflict)
    return parent


def merge_one(parent: Schema, child: Schema, *, conflict: MergeFlags = MergeFlags.OVERWRITE) -> Schema:
    """
    Merge a child Schema into a parent Schema, optionally overwriting any existing keys.

    Parameters
    ----------
    parent : Schema
    child : Schema
    conflict : MergeFlags
        Specifies what to do if a key is found both in parent and child:
            IGNORE: keep the value of parent
            EXCEPTION: throw an exception
            OVERWRITE: keep the value of child, discarding the value of parent (default)
            FUSE: allow both values from parent's and child's schema

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
            match conflict:
                case MergeFlags.IGNORE:
                    pass
                case MergeFlags.EXCEPTION:
                    raise schema.SchemaError(f"Key collision for {key}")
                case MergeFlags.OVERWRITE:
                    parent._schema[key] = child._schema[key]
                case MergeFlags.FUSE:
                    parent._schema[key] = Or(parent._schema[key], child._schema[key])
        else:
            parent._schema[key] = child._schema[key]

    return parent
