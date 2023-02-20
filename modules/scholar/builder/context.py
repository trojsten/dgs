import os
import sys
import collections
from pathlib import Path
from abc import ABCMeta, abstractmethod

sys.path.append('.')

from core.builder import context
from core.utils import crawler


class ContextScholar(context.FileSystemContext, metaclass=ABCMeta):
    def ident(self, course=None, year=None, target_type=None, issue=None):
        return (
            self.default(course),
            self.default(year, lambda x: f'{x:04d}'),
            self.default(target_type),
            self.default(issue, lambda x: f'{x:02d}'),
        )

    def node_path(self, course=None, year=None, target_type=None, issue=None, *deeper):
        return Path(self.root, *self.ident(course, year, target_type, issue), *deeper)


class ContextModule(ContextScholar):
    def __init__(self, module):
        self.add_id(module)


class ContextCourse(ContextScholar):
    def populate(self, course):
        self.load_meta(course).add_id(course)


class ContextYear(ContextScholar):
    def populate(self, course, year):
        self.load_meta(course, year) \
            .add_id(f'{year:04d}') \
            .add_number(year)


class ContextIssue(ContextScholar):
    def populate(self, course, year, target, issue):
        self.name(course, year, target, issue)
        self.load_meta(course, year, target, issue) \
            .add_id(f'{issue:02d}') \
            .add_number(issue)
        self.add_subdirs(
            self.subcontext_class,
            self.subcontext_name,
            (self.root, course, year, target, issue),
            (self.root, course, year, target, issue),
        )


class ContextHandoutProblem(ContextScholar):
    def populate(self, course, year, target, issue, sub):
        self.name(course, year, target, issue, sub)
        self.add_id(sub)


class ContextHandoutIssue(ContextIssue):
    subcontext_name = 'problems'
    subcontext_class = ContextHandoutProblem


class ContextIssueSub(ContextScholar):
    def populate(self, course, year, target, issue, sub):
        self.name(course, year, target, issue, sub)
        self.load_meta(course, year, target, issue, sub) \
            .add_id(sub)
        self.add_subdirs(
            self.subcontext_class,
            self.subcontext_name,
            (self.root, course, year, target, issue, sub),
            (self.root, course, year, target, issue, sub),
        )


class ContextIssueSubSub(ContextScholar):
    def __init__(self, course, year, target, issue, sub, subsub):
        self.name(course, year, target, issue, sub, subsub)
        self.load_meta(course, year, target, issue, sub, subsub) \
            .add_id(subsub)


class ContextHandoutSubSub(ContextScholar):
    def __init__(self, course, year, target, issue, sub, subsub):
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
    def populate(self, course, year, issue):
        self.adopt('module', ContextModule('scholar'))
        self.adopt('course', ContextCourse(self.root, course))
        self.adopt('year', ContextYear(self.root, course, year))
        self.adopt('issue', self.issue_context_class(self.root, course, year, self.target, issue))


class ContextHomework(ContextIssueBase):
    target = 'homework'
    issue_context_class = ContextHomeworkIssue


class ContextHandout(ContextIssueBase):
    target = 'handouts'
    issue_context_class = ContextHandoutIssue


""" Single lecture contexts start here """

class ContextScholarSingle(context.Context):
    @staticmethod
    def node_path(root, course='', lecture='', part='', problem=''):
        return Path(root, course, lecture, part, problem)


class ContextScholarLecture(ContextScholarSingle):
    def __init__(self, course, lecture):
        super().__init__()
        self.load_meta(course, lecture)
        self.adopt('module', ContextSingleModule('scholar'))
        self.adopt('course', ContextSingleCourse(root, course))
        self.adopt('lecture', ContextSingleLecture(root, course, lecture))
        self.crawler = crawler.Crawler(Path(root, course, lecture))

        if 'parts' in self.data:
            self.add({'parts': [ContextScholarPart(root, course, lecture, part).data for part in self.data['parts']]})
        else:
            self.add_subdirs(ContextScholarPart, 'parts', root, course, lecture)


class ContextScholarPart(ContextScholarSingle):
    def populate(self, course, lecture, part):
        self.name(course, lecture, part)
        self.load_meta(course, lecture, part) \
            .add_id(part)
        self.add_subdirs(ContextScholarProblem, 'problems', root, course, lecture, part)


class ContextScholarProblem(ContextScholarSingle):
    def populate(self, course, lecture, part, problem):
        self.name(course, lecture, part, problem)
        self.load_meta(course, lecture, part, problem) \
            .add_id(problem)
        self.add({'has_problem': Path(root, course, lecture, part, problem, 'problem.md').is_file()})
        self.add({'has_solution': Path(root, course, lecture, part, problem, 'solution.md').is_file()})


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
        self.add({'has_abstract': Path(root, course, lecture, 'abstract.md').is_file()})


class ContextDir(context.Context):
    def __init__(self, root, *deeper):
        self.load_meta(root, *deeper) \
            .add_id(deeper[-1] if deeper else root)

        crawl = crawler.Crawler(Path(root, *deeper))
        self.add({'children': ContextDir(root, *deeper, child).data for child in crawl.children()})

    @staticmethod
    def node_path(*args):
        return Path(*args)
