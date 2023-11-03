from typing import Iterable


def merge(parent: dict, *children: Iterable[dict], overwrite: bool = True) -> dict:
    for child in children:
        parent = merge_one(parent, child, overwrite=overwrite)
    return parent


def merge_one(parent: dict | object, child: dict | object, *, overwrite: bool = True) -> dict:
    if id(parent) == id(child):
        return parent

    if parent is None:
        return child

    for key in child:
        if key in parent:
            if overwrite:
                if isinstance(parent[key], dict) and isinstance(child[key], dict):
                    merge_one(parent[key], child[key])
                else:
                    parent[key] = child[key]
        else:
            parent[key] = child[key]

    return parent
