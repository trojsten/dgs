import yaml
import os
import sys
import pprint
import argparse

import core.utilities.dicts as dicts
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.jinja as jinja

class BaseBuilder():
    def __init__(self):
        self.createArgParser()
        self.parseArgs()

        self.launchDirectory    = os.path.realpath(self.args.launch)
        self.templateRoot       = os.path.realpath(self.args.templateRoot)
        self.outputDirectory    = os.path.realpath(self.args.output) if self.args.output else None

    def printDebugInfo(self):
        if self.args.debug:
            print("Launched {target} builder in {dir}".format(
                target  = c.name(self.target),
                dir     = c.path(self.args.launch),
            ))
            print(c.act("Content templates:"))
            pprint.pprint(self.templates)

            print(c.act("Context:"))
            self.context.print()
        
    def createArgParser(self):
        self.parser = argparse.ArgumentParser(
            description             = "Prepare a DGS input dataset from repository",
        )
        self.parser.add_argument('launch',              action = argparser.readableDir) 
        self.parser.add_argument('templateRoot',        action = argparser.readableDir)
        self.parser.add_argument('-o', '--output',      action = argparser.writeableDir) 
        self.parser.add_argument('-d', '--debug',       action = 'store_true')
        return self.parser

    def parseArgs(self):
        self.args = self.parser.parse_args()
       
    def build(self):
        self.printDebugInfo()
        self.printBuildInfo()

        for dir, templates in self.templates.items():
            for template in templates:
                jinja.printTemplate(os.path.join(self.templateRoot, dir), template, self.context.data, self.outputDirectory)

        print(c.ok("Template builder successful"))


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
            filename = os.path.join(*args)
            contents = yaml.load(open(filename, 'r'))
            result = {} if contents is None else contents
        except FileNotFoundError as e:
            print(c.err("[FATAL] Could not load YAML file"), c.path(filename))
            raise e

        self.data = contents
        return self

    def loadMeta(self, *args):
        return self.loadYaml(self.nodePath(*args), 'meta.yaml')

    def nodePath(self, *args):
        raise NotImplementedError("nodePath is not implemented")

    def print(self):
        pprint.pprint(self.data)

    def setNumber(self):
        return self.add({'number': self.number})

    def addNumber(self, number):
        return self.add({'number': number})

    def setId(self):
        return self.add({'id': self.id})

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
