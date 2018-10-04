#!/usr/bin/env python3

import os, sys, pprint

sys.path.append('.')
import core.utilities.jinja as jinja
import core.utilities.dicts as dicts
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

class ContextHomework(context.Context):
    def __init__(self, course, year, issue):
        super().__init__()
        self.course = course
        self.year   = year
        self.issue  = issue

        self.add(ContextModule('scholar'))
        self.add(ContextCourse(course))
        self.add(ContextYear(year))
        self.add(ContextIssue(issue))


class ContextModule(context.Context):
    def __init__(self, module):
        super().__init__()
        self.add({'module': module})

class ContextCourse(context.Context):
    def __init__(self, year):
        super().__init__()
        self.add({'': year})

class ContextYear(context.Context):
    def __init__(self, year):
        super().__init__()
        self.add({'year': year})
    
class ContextIssue(context.Context):
    def __init__(self, course, year, issue):
        super().__init__()
        self.load()

#class ScholarBuilder(ContextBuilder):
#    def parser()
#    pass


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
    output = context.loadMeta(nodePathScholarHandout, (root, course))
    return dicts.merge(output, {
        'id':           course,
    })

def yearContext(root, course, year):
    return {
        'id':           year,
    }

def lessonContext(root, course, year, lesson):
    output = context.loadMeta(nodePathScholarHandout, (root, course, year, lesson))
    output = context.addId(output, '{:02d}'.format(lesson))
    return context.addNumber(output, lesson)

def handoutContext(root, course, year, lesson):
    handout = {
        'module':       moduleContext(),
        'course':       courseContext(root, course),
        'year':         yearContext(root, course, year),
        'lesson':       lessonContext(root, course, year, lesson),
    }

    return handout

