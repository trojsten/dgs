#!/usr/bin/env python3

import yaml, os, sys

def mergeDicts(parent, *children):
    for child in children:
        parent = mergeDict(parent, child)
    return parent

def mergeDict(parent, child):
    if parent is None:
        return child
    for key in child:
        if key in parent:
            if isinstance(parent[key], dict) and isinstance(parent[key], dict):
                mergeDict(parent[key], child[key])
            else:
                parent[key] = child[key]
        else:
            parent[key] = child[key]
    return parent

def isNode(path):
    return (os.path.isdir(path) and os.path.basename(os.path.normpath(path))[0] != '.')

def listChildNodes(node):
    return list(filter(lambda child: isNode(os.path.join(node, child)), sorted(os.listdir(node))))

def loadYaml(*args):
    nargs = [x if type(x) is str else '{:02d}'.format(x) for x in args]
    try:
       result = yaml.load(open(os.path.join(*args), 'r'))
       if result is None:
           result = {}
    except FileNotFoundError as e:
        print(Fore.RED + "[FATAL] Could not load YAML file: {}".format(e) + Style.RESET_ALL)
        raise e
    return result

def loadMeta(pathfinder, args):
    try:
       result = yaml.load(open(os.path.join(pathfinder(*args), 'meta.yaml'), 'r'))
       if result is None:
           result = {}
    except FileNotFoundError as e:
        print(Fore.RED + "[FATAL] Could not load metadata file: {}".format(e) + Style.RESET_ALL)
        raise e
    return result


def splitMod(what, step, first = 0):
    result = [[] for i in range(0, step)]
    for i, item in enumerate(what):
        result[(i + first) % step].append(item)
    return result

def splitDiv(what, step):
    return [] if what == [] else [what[0:step]] + splitDiv(what[step:], step)

def addNumbers(what, start = 0):
    result = []
    num = start
    for item in what:
        result.append({
            'number': num,
            'id': item,
        })
        num += 1
    return result

def numerate(objects, start = 0):
    num = start
    for item in objects:
        mergeDicts(item, {
            'number': num
        })
        num += 1
    return objects

