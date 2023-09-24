import os
import sys

sys.path.append('.')

from core.utilities import context


class ContextScholar(context.Context):
    def node_path(self, root, course=None, year=None, target_type=None, issue=None):
        return os.path.join(
            root,
            '' if course is None else course,
            '' if year is None else f'{year:04d}',
            '' if target_type is None else target_type,
            '' if issue is None else f'{issue:02d}',
        )


class ContextScholarBase(ContextScholar):
    def __init__(self, root, course, year):
        super().__init__()
        self.absorb('module', ContextModule('scholar'))
        self.absorb('course', ContextCourse(root, course))
        self.absorb('year', ContextYear(root, course, year))


class ContextHomework(ContextScholarBase):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year)
        self.absorb('issue', ContextIssue(root, course, year, 'homework', issue))


class ContextHandout(ContextScholarBase):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year)
        self.absorb('issue', ContextIssue(root, course, year, 'handouts', issue))


class ContextModule(ContextScholar):
    def __init__(self, module):
        super().__init__()
        self.add_id(module)


class ContextCourse(ContextScholar):
    def __init__(self, root, course):
        super().__init__()
        self.load_meta(root, course).add_id(course)


class ContextYear(ContextScholar):
    def __init__(self, root, course, year):
        super().__init__()
        self.load_meta(root, course, year) \
            .add_id(f'{year:04d}') \
            .add_number(year)


class ContextIssue(ContextScholar):
    def __init__(self, root, course, year, target, issue):
        super().__init__()
        self.load_meta(root, course, year, target, issue) \
            .add_id(f'{issue:02d}') \
            .add_number(issue)


class ContextScholarSingle(context.Context):
    def node_path(self, root, course=None, lecture=None):
        return os.path.join(
            root,
            '' if course is None else course,
            '' if lecture is None else lecture,
        )


class ContextScholarLecture(ContextScholarSingle):
    def __init__(self, root, course, lecture):
        super().__init__()
        self.absorb('module', ContextSingleModule('scholar'))
        self.absorb('course', ContextSingleCourse(root, course))
        self.absorb('lecture', ContextSingleLecture(root, course, lecture))


class ContextSingleModule(ContextScholarSingle):
    def __init__(self, module):
        super().__init__()
        self.add_id(module)


class ContextSingleCourse(ContextScholarSingle):
    def __init__(self, root, course):
        super().__init__()
        self.load_meta(root, course).add_id(course)


class ContextSingleLecture(ContextScholarSingle):
    def __init__(self, root, course, lecture):
        super().__init__()
        self.load_meta(root, course, lecture).add_id(lecture)
