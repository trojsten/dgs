import os
import sys

sys.path.append('.')
import core.utilities.colour as c
import core.utilities.context as context

class BuilderScholar(context.BaseBuilder):
    module = 'scholar'

    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('course',               type = str, choices = ['TA1', 'TA2'])
        self.parser.add_argument('year',                 type = int)
        self.parser.add_argument('issue',                type = int)

    def id(self):
        return (self.args.course, self.args.year, self.args.issue)

    def path(self):
        return (self.args.course, f'{self.args.year:04d}', self.subdir, f'{self.args.issue:02d}')
   

class BuilderSingle(context.BaseBuilder):
    module = 'scholar'

    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('course', type = str, choices = ['FKS'])
        self.parser.add_argument('lecture', type = str)

    def id(self):
        return (self.args.course, self.args.lecture)

    def path(self):
        return (self.args.course, self.args.lecture)


class ContextScholar(context.Context):
    def nodePath(self, root, course = None, year = None, targetType = None, issue = None):
        return os.path.join(
            root,
            '' if course        is None else course,
            '' if year          is None else f'{year:04d}',
            '' if targetType    is None else targetType,
            '' if issue         is None else f'{issue:02d}',
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
            .addId(f'{year:04d}') \
            .addNumber(year)

class ContextIssue(ContextScholar):
    def __init__(self, root, course, year, target, issue):
        super().__init__()
        self.loadMeta(root, course, year, target, issue) \
            .addId(f'{issue:02d}') \
            .addNumber(issue)


class ContextScholarSingle(context.Context):
    def nodePath(self, root, course = None, lecture = None):
        return os.path.join(
            root,
            '' if course    is None else course,
            '' if lecture   is None else lecture,
        )

class ContextScholarLecture(ContextScholarSingle):
    def __init__(self, root, course, lecture):
        super().__init__()
        self.absorb('module',   ContextSingleModule   ('scholar'))
        self.absorb('course',   ContextSingleCourse   (root, course))
        self.absorb('lecture',  ContextSingleLecture  (root, course, lecture))

class ContextSingleModule(ContextScholarSingle):
    def __init__(self, module):
        super().__init__()
        self.addId(module)

class ContextSingleCourse(ContextScholarSingle):
    def __init__(self, root, course):
        super().__init__()
        self.loadMeta(root, course).addId(course)

class ContextSingleLecture(ContextScholarSingle):
    def __init__(self, root, course, lecture):
        super().__init__()
        self.loadMeta(root, course, lecture).addId(lecture)

