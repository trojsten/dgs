import os, sys, pprint

sys.path.append('.')
import core.utilities.jinja as jinja
import core.utilities.dicts as dicts
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

class ContextScholar(context.Context):
    def __init__(self, root, course, year, issue):
        super().__init__()
        self.absorb('module',   ContextModule   ('scholar'))
        self.absorb('course',   ContextCourse   (root, course))
        self.absorb('year',     ContextYear     (root, course, year))

class ContextHandout(ContextScholar):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year, issue)
        self.absorb('issue',    ContextIssue    (root, course, year, 'handouts', issue))

class ContextHomework(ContextScholar):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year, issue)
        self.absorb('issue',    ContextIssue    (root, course, year, 'homework', issue))

class ContextModule(context.Context):
    def __init__(self, module):
        super().__init__()
        self.addId(module)

class ContextCourse(context.Context):
    def __init__(self, root, course):
        super().__init__()
        self.loadYaml(root, course, 'meta.yaml').addId(course)
        
class ContextYear(context.Context):
    def __init__(self, root, course, year):
        super().__init__()
        self.loadYaml(root, course, '{:04d}'.format(year), 'meta.yaml').addId(year)

class ContextIssue(context.Context):
    def __init__(self, root, course, year, target, issue):
        super().__init__()
        id = '{:02d}'.format(issue)
        self.loadYaml(root, course, '{:04d}'.format(year), target, id, 'meta.yaml').addId(id).addNumber(issue)
    
def createScholarParser():
    parser = argparser.createGenericParser()
    parser.add_argument('course',               choices = ['TA1'])
    parser.add_argument('year',                 type = int)
    parser.add_argument('issue',                type = int)

    return parser

