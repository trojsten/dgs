import os
import subprocess
from schema import Schema, And, Or, Regex

import core.utilities.globals as glob


def string(x: str) -> And:
    """ Is non-empty string """
    return And(str, len)


def valid_language(code: str) -> bool:
    return code in glob.languages.keys()


def commit_hash(code: str) -> Regex:
    return Regex(r'[a-f0-9]+')


def check_output(command, *, cwd) -> str:
    return subprocess.check_output(command, cwd=cwd if cwd is not None else os.getcwd()).decode().rstrip("\n")


def get_last_commit_hash(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--short", "--verify", "master"], cwd=cwd)


def get_branch(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--symbolic-full-name", "--abbrev-ref", "HEAD"], cwd=cwd)


def merge(parent: Schema, *children: Schema) -> Schema:
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
