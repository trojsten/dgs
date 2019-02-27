import os
import sys

sys.path.append('.')
import core.utilities.colour as c
import core.utilities.context as context

class BuilderScholar(context.BaseBuilder):
    module = 'scholar'

    def __init__(self):
        super().__init__()

    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('course',               choices = ['TA1', 'TA2'])
        self.parser.add_argument('year',                 type = int)
        self.parser.add_argument('issue',                type = int)

    def id(self):
        return (self.args.course, self.args.year, self.args.issue)

    def path(self):
        return (self.args.course, '{:04d}'.format(self.args.year), 'handouts', '{:02d}'.format(self.args.issue))
    
class ContextScholar(context.Context):
    def nodePath(self, root, course = None, year = None, targetType = None, issue = None):
        return os.path.join(
            root,
            '' if course        is None else course,
            '' if year          is None else '{:04d}'.format(year),
            '' if targetType    is None else targetType,
            '' if issue         is None else '{:02d}'.format(issue),
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
        self.loadMeta(root, course, year) \
            .addId('{:04d}'.format(year)) \
            .addNumber(year)

class ContextIssue(ContextScholar):
    def __init__(self, root, course, year, target, issue):
        super().__init__()
        self.loadMeta(root, course, year, target, issue) \
            .addId('{:02d}'.format(issue)) \
            .addNumber(issue)


