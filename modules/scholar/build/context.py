import os
import sys
import collections
from pathlib import Path

sys.path.append('.')

from core.utilities import context


class ContextScholar(context.Context):
    def node_path(self, root, course=None, year=None, target_type=None, issue=None, *deeper_levels):
        return os.path.join(
            root,
            '' if course is None else course,
            '' if year is None else f'{year:04d}',
            '' if target_type is None else target_type,
            '' if issue is None else f'{issue:02d}',
            *deeper_levels
        )

    def add_subdirs(self, subcontext_class, subcontext_key, *subcontext_args):
        subdirs = sorted([subdir.name for subdir in Path(self.node_path(*subcontext_args)).iterdir() if subdir.is_dir()])
        self.add({subcontext_key: [subcontext_class(*subcontext_args, subdir).data for subdir in subdirs]})


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
        self.add_subdirs(self.subcontext_class, self.subcontext_name, root, course, year, target, issue)


class ContextHandoutProblem(ContextScholar):
    def __init__(self, root, course, year, target, issue, sub):
        super().__init__()
        self.add_id(sub)


class ContextHandoutIssue(ContextIssue):
    subcontext_name = 'problems'
    subcontext_class = ContextHandoutProblem




class ContextIssueSub(ContextScholar):
    def __init__(self, root, course, year, target, issue, sub):
        super().__init__()
        self.load_meta(root, course, year, target, issue, sub) \
            .add_id(sub)
        self.add_subdirs(self.subcontext_class, self.subcontext_name, root, course, year, target, issue, sub)


class ContextIssueSubSub(ContextScholar):
    def __init__(self, root, course, year, target, issue, sub, subsub):
        super().__init__()
        self.load_meta(root, course, year, target, issue, sub, subsub) \
            .add_id(subsub)


class ContextHandoutSubSub(ContextScholar):
    def __init__(self, root, course, year, target, issue, sub, subsub):
        super().__init__()
        self.add_id(subsub)


# Homework and its subcontexts
class ContextHomeworkProblem(ContextIssueSub):
    subcontext_name = 'subproblems'
    subcontext_class = ContextIssueSubSub


class ContextHomeworkIssue(ContextIssue):
    subcontext_name = 'problems'
    subcontext_class = ContextHomeworkProblem





class ContextIssueBase(ContextScholar):
    def __init__(self, root, course, year, issue):
        super().__init__()
        self.absorb('module', ContextModule('scholar'))
        self.absorb('course', ContextCourse(root, course))
        self.absorb('year', ContextYear(root, course, year))
        self.absorb('issue', self.issue_context_class(root, course, year, self.target, issue))


class ContextHomework(ContextIssueBase):
    target = 'homework'
    issue_context_class = ContextHomeworkIssue


class ContextHandout(ContextIssueBase):
    target = 'handouts'
    issue_context_class = ContextHandoutIssue


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
