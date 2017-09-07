import argparse, yaml, os, jinja2, sys
from colorama import Fore, Style

def mergeDicts(parent, *children):
    for child in children:
        mergeDict(parent, child)
    return parent

def mergeDict(parent, child):
    for key in child:
        if key in parent:
            if isinstance(parent[key], dict) and isinstance(parent[key], dict):
                mergeDict(parent[key], child[key])
            else:
                parent[key] = child[key]
        else:
            parent[key] = child[key]
    return parent

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

    env.filters['roman'] = roman
    env.filters['formatList'] = formatList
    return env

def roman(what):
    what = int(what)
    if what == 0:
        return '0'
    if what > 4000:
        raise ValueError("Argument must be between 1 and 3999")

    ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
    nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
    result = ""
    for i in range(len(ints)):
        count = int(what / ints[i])
        result += nums[i] * count
        what -= ints[i] * count
    return result

def formatList(list):
    return renderList(list, textbf = True)

def renderList(what, **kwargs):
    if (type(what) == str):
        what = [what]

    textbf = kwargs.get('textbf', False)

    if textbf:
        what = ['\\textbf{{{}}}'.format(x) for x in what if x != '']

    for i, item in enumerate(what[:-2]):
        what[i] = '{},'.format(item)

    if len(what) > 1:
        what[-2] = '{} a'.format(what[-2])
    
    return ' '.join(what)

def splitMod(what, step, first = 0):
    result = [[] for i in range(0, step)]
    for i, item in enumerate(what):
        result[(i + first) % step].append(item)
    return result

def splitDiv(what, step):
    return [] if what == [] else [what[0:step]] + splitDiv(what[step:], step)

def loadYaml(*args):
 #   try:
    result = yaml.load(open(os.path.join(*args), 'r'))
 #   except FileNotFoundError as e:
 #       print(Fore.RED + "[FATAL] Could not load YAML file: {}".format(e) + Style.RESET_ALL)
 #       sys.exit(-1)
    return result

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
    def __call__(self, parser, namespace, values, option_string=None):
        tryDir = values
        if not os.path.isdir(tryDir):
            raise argparse.ArgumentTypeError("readableDir: {0} is not a valid path".format(tryDir))
        if os.access(tryDir, os.R_OK):
            setattr(namespace, self.dest, tryDir)
        else:
            raise argparse.ArgumentTypeError("readableDir: {0} is not a readable directory".format(tryDir))

