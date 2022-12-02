from typing import Iterable, Dict


def merge(parent: Dict, *children: Iterable[Dict]) -> Dict:
    for child in children:
        parent = merge_one(parent, child)
    return parent


def merge_one(parent: Dict, child: Dict) -> Dict:
    if id(parent) == id(child):
        raise RecursionError("Cannot merge a context with itself")

    if parent is None:
        return child

    for key in child:
        if key in parent:
            if isinstance(parent[key], dict) and isinstance(child[key], dict):
                merge_one(parent[key], child[key])
            else:
                parent[key] = child[key]
        else:
            parent[key] = child[key]

    return parent
