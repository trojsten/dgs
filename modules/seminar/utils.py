#!/usr/bin/python3

import argparse, yaml, os, jinja2

def mergeInto(a, b):
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                mergeInto(a[key], b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

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

def splitBy(what, step):
    result = [[] for i in range(0, step)]
    for i, item in enumerate(what):
        result[(i + 1) % step].append(item)
    return result

class readableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        tryDir = values
        if not os.path.isdir(tryDir):
            raise argparse.ArgumentTypeError("readableDir: {0} is not a valid path".format(tryDir))
        if os.access(tryDir, os.R_OK):
            setattr(namespace, self.dest, tryDir)
        else:
            raise argparse.ArgumentTypeError("readableDir: {0} is not a readable directory".format(tryDir))

