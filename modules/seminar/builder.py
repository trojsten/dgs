#!/usr/bin/python3

import argparse, yaml, os, jinja2, sys
from utils import jinjaEnv, mergeIntoDict

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ round from repository",
)
parser.add_argument('seminar', choices = ['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX'])
parser.add_argument('volume', type = int)
parser.add_argument('part', type = int, choices = [1, 2])
parser.add_argument('round', type = int, choices = [1, 2, 3])
args = parser.parse_args()

try:
    seminarMeta = yaml.load(open('../../source/{seminar}/meta.yaml'.format(seminar = args.seminar), 'r'))
    volumeMeta = yaml.load(open('../../source/{seminar}/{volume}/meta.yaml'.format(seminar = args.seminar, volume = args.volume), 'r'))
    partMeta = yaml.load(open('../../source/{seminar}/{volume}/{part}/meta.yaml'.format(seminar = args.seminar, volume = args.volume, part = args.part), 'r'))
    roundMeta = yaml.load(open('../../source/{seminar}/{volume}/{part}/{round}/meta.yaml'.format(seminar = args.seminar, volume = args.volume, part = args.part, round = args.part), 'r'))
except FileNotFoundError as e:
    print("Could not open file {}".format(e))
    sys.exit(-1)

context = {
    'seminar': seminarMeta,
    'part': partMeta,
    'round': roundMeta,
}

update = {
    'seminar': {
        'id': args.seminar,
    },
    'round': {
        'id': args.round,
    },
    'part': {
        'id': args.part,
        'genitive': ['zimnej', 'letnej'][args.part - 1],
    },
}

context = mergeIntoDict(context, update)

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
	loader = jinja2.FileSystemLoader('templates')
)

print(jinjaEnv('templates').get_template('problems.tex').render(context))
