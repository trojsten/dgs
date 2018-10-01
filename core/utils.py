#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys
from colorama import Fore, Style

sys.path.append('.')

import core.filters

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

def jinjaEnv(directory):
    env = jinja2.Environment(
        block_start_string = '(@',
        block_end_string = '@)',
        variable_start_string = '(*',
        variable_end_string = '*)',
        comment_start_string = '\#{',
        comment_end_string = '}',
        line_statement_prefix = '%%',
        line_comment_prefix = '%#',
        trim_blocks = True,
        autoescape = False,
        loader = jinja2.FileSystemLoader(directory),
    )

    mergeDicts(env.filters, {
        'roman':        core.filters.roman,
        'formatList':   core.filters.formatList,
    })

    return env

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

class readableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tryDir = values
        if not os.path.isdir(tryDir):
            raise argparse.ArgumentTypeError("readableDir: {0} is not a valid path".format(tryDir))
        if os.access(tryDir, os.R_OK):
            setattr(namespace, self.dest, tryDir)
        else:
            raise argparse.ArgumentTypeError("readableDir: {0} is not a readable directory".format(tryDir))

class writeableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tryDir = values
        if not os.path.isdir(tryDir):
            raise argparse.ArgumentTypeError("readableDir: {0} is not a valid path".format(tryDir))
        if os.access(tryDir, os.W_OK):
            setattr(namespace, self.dest, tryDir)
        else:
            raise argparse.ArgumentTypeError("readableDir: {0} is not a writeable directory".format(tryDir))
