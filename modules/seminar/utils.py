#!/usr/bin/python3

import argparse, yaml, os, jinja2

def mergeIntoDict(a, b):
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                mergeIntoDict(a[key], b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

def jinjaEnv(directory):
    return jinja2.Environment(
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
	loader = jinja2.FileSystemLoader(directory)
    )

def renderList(what, **kwargs):
    textbf = kwargs.get('textbf', False)

    if textbf:
        what = ['\\textbf{{{}}}'.format(x) for x in what]

    for i, item in enumerate(what[:-2]):
        what[i] = '{},'.format(item)

    if len(what) > 1:
        what[-2] = '{} a'.format(what[-2])
    
    return ' '.join(what)
