#!/usr/bin/env python3

import os, sys, pprint

sys.path.append('.')
import build
import core.utilities.jinja as jinja
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

def createScholarParser(target):
    parser = argparser.createGenericParser()
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
    if lesson is None:
        return os.path.join(root, course or '', year or '') 
    else:
        return os.path.join(root, course, '{:04d}'.format(year), 'handout', '{:02d}'.format(lesson))

def moduleContext():
    return {
        'id':           'scholar',
    }

def courseContext(root, course):
    return context.loadMeta(nodePathScholarHandout, (root, course)),

def yearContext(root, course, year):
    return {
        'year':         year,
    }

def lessonContext(root, course, year, lesson):
    return context.loadMeta(nodePathScholarHandout, (root, course, year, lesson))

def handoutContext(root, course, year, lesson):
    handout = {
        'module':       moduleContext(),
        'course':       courseContext(root, course),
        'lesson':       lessonContext(root, course, year, lesson),
    }

    return handout

