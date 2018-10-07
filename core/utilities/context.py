import yaml, os, sys, pprint

import core.utilities.dicts as dicts
import core.utilities.colour as c

class Context():
    def __init__(self):
        self.data = {}

    def add(self, *args):
        self.data = dicts.merge(self.data, *args)
        return self

    def absorb(self, key, ctx):
        self.data[key] = dicts.merge(self.data.get(key), ctx.data)
        return self

    def loadYaml(self, *args):
        try:
            contents = yaml.load(open(os.path.join(*args), 'r'))
            result = {} if contents is None else contents
        except FileNotFoundError as e:
            print(c.err("[FATAL] Could not load YAML file"), c.path(e))
            raise e

        self.data = contents
        return self

    def loadMeta(self, *args):
        return self.loadYaml(*args, 'meta.yaml')

    def print(self):
        pprint.pprint(self.data)

    def addNumber(self, number):
        return self.add({'number': number})

    def addId(self, id):
        return self.add({'id': id})


def isNode(path):
    return (os.path.isdir(path) and os.path.basename(os.path.normpath(path))[0] != '.')

def listChildNodes(node):
    return list(filter(lambda child: isNode(os.path.join(node, child)), sorted(os.listdir(node))))

def loadYaml(*args):
    try:
       result = yaml.load(open(os.path.join(*args), 'r'))
       if result is None:
           result = {}
    except FileNotFoundError as e:
        print(c.err("[FATAL] Could not load YAML file", c.path(e)))
        raise e
    return result

def loadMeta(pathfinder, args):
    try:
       result = yaml.load(open(os.path.join(pathfinder(*args), 'meta.yaml'), 'r'))
       if result is None:
           result = {}
    except FileNotFoundError as e:
        print(c.err("[FATAL] Could not load metadata file)", c.path(e)))
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
