def merge(parent, *children):
    for child in children:
        parent = mergeOne(parent, child)
    return parent

def mergeOne(parent, child):
    if parent is None:
        return child
    for key in child:
        if key in parent:
            if isinstance(parent[key], dict) and isinstance(parent[key], dict):
                mergeOne(parent[key], child[key])
            else:
                parent[key] = child[key]
        else:
            parent[key] = child[key]

    return parent

