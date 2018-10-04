#!/usr/bin/env python3

import yaml, os, sys, pprint

import core.utilities.dicts as dicts

class Context():
    def __init__(self):
        self.data = {}

    def add(self, *args):
        dicts.merge(self.data, *args)
        return self

    def loadYaml(*args):
        try:
            contents = yaml.load(open(os.path.join(*args), 'r'))
            result = {} if contents is None else contents
        except FileNotFoundError as e:
            print(c.err("[FATAL] Could not load YAML file"), c.path(e))
            raise e

        self.data = contents
        return self

    def print(self):
        pprint.pprint(self.data)

    def addId(self, id):
        self.add({'id': id})



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
        dicts.merge(item, {
            'number': num
        })
        num += 1
    return objects

def addNumber(ctx, num):
    return dicts.merge(ctx, {
        'number': num,
    })

def addId(ctx, id):
    return dicts.merge(ctx, {
        'id':   id,
    })
