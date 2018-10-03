#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama

sys.path.append('.')

import core.builder
from core.utils import *

def createScholarParser(target):
    parser = core.builder.createGenericParser()
    parser.add_argument('course',               choices = ['TA1'])
    parser.add_argument('year',                 type = int)
    if target == 'handout':
        parser.add_argument('lesson',           type = int)
    elif target == 'homework':
        parser.add_argument('issue',            type = int)
    else:
        raise KeyError("Unknown scholar parser target {}".format(target))

    return parser

def nodePathScholarHandout(root, course = None, year = None, lesson = None):
    return os.path.join(root, course, '{:04d}'.format(year), 'handout', '{:02d}'.format(lesson))

def handoutContext(root, course, year, lesson):
    handout = loadMeta(nodePathScholarHandout, (root, course, year, lesson))
    return  mergeDicts(handout, {
        'lesson': '{:02d}'.format(lesson),
        'course': course,
    })
