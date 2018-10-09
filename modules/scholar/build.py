import os, sys, pprint

sys.path.append('.')
import core.utilities.jinja as jinja
import core.utilities.dicts as dicts
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

def createScholarParser():
    parser = argparser.createGenericParser()
    parser.add_argument('course',               choices = ['TA1'])
    parser.add_argument('year',                 type = int)
    parser.add_argument('issue',                type = int)
    return parser

class ContextScholar(context.Context):
    def nodePath(self, root, course = None, year = None, targetType = None, issue = None):
        return os.path.join(
            root,
            '' if course        is None else course,
            '' if year          is None else '{:04d}'.format(year),
            '' if targetType    is None else targetType,
            '' if issue         is None else '{:02d}'.format(issue)
        )

class ContextScholarBase(ContextScholar):
    def __init__(self, root, course, year):
        super().__init__()
        self.absorb('module',   ContextModule   ('scholar'))
        self.absorb('course',   ContextCourse   (root, course))
        self.absorb('year',     ContextYear     (root, course, year))

class ContextHomework(ContextScholarBase):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year)
        self.absorb('issue',    ContextIssue    (root, course, year, 'homework', issue))

class ContextHandout(ContextScholarBase):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year)
        self.absorb('issue',    ContextIssue    (root, course, year, 'handouts', issue))

class ContextModule(ContextScholar):
    def __init__(self, module):
        super().__init__()
        self.addId(module)

class ContextCourse(ContextScholar):
    def __init__(self, root, course):
        super().__init__()
        self.loadMeta(root, course).addId(course)
        
class ContextYear(ContextScholar):
    def __init__(self, root, course, year):
        super().__init__()
        self.id = '{:04d}'.format(year)
        self.loadMeta(root, course, year) \
            .addId(self.id) \
            .addNumber(year)

class ContextIssue(ContextScholar):
    def __init__(self, root, course, year, target, issue):
        super().__init__()
        self.id = '{:02d}'.format(issue)
        self.number = issue
        self.loadMeta(root, course, year, target, issue) \
            .addId(self.id) \
            .addNumber(issue)


