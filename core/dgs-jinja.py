#!/usr/bin/env python3

import argparse, yaml, os, jinja2

parser = argparse.ArgumentParser(
    description = "Render a DeGeŠ Jinja2 template using a YAML file as a context",
)
parser.add_argument('template', type = argparse.FileType('r'))
parser.add_argument('context', type = argparse.FileType('r'))
args = parser.parse_args()

path, name = os.path.split(os.path.abspath(args.template.name))

print("Path is {}, name is {}".format(path, name))

latex_jinja_env = jinja2.Environment(
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
	loader = jinja2.FileSystemLoader(path or './')
)
template = latex_jinja_env.get_template(name)
print(template.render(yaml.load(args.context)))

