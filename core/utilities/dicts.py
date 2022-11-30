def merge(parent, *children):
    for child in children:
        parent = merge_one(parent, child)
    return parent


def merge_one(parent, child):
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
