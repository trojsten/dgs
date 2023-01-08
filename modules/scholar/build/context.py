import os
import sys
import collections
from pathlib import Path

sys.path.append('.')

from core.builder import context
from core.utils import crawler


class ContextScholar(context.Context):
    @staticmethod
    def node_path(root, course=None, year=None, target_type=None, issue=None, *deeper):
        return Path(
            root,
            '' if course is None else course,
            '' if year is None else f'{year:04d}',
            '' if target_type is None else target_type,
            '' if issue is None else f'{issue:02d}',
            *deeper
        )


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
        self.add_subdirs(self.subcontext_class, self.subcontext_name, (root, course, year, target, issue), (root, course, year, target, issue))


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
        self.add_subdirs(self.subcontext_class, self.subcontext_name, (root, course, year, target, issue, sub), (root, course, year, target, issue, sub))


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
        self.adopt('module', ContextModule('scholar'))
        self.adopt('course', ContextCourse(root, course))
        self.adopt('year', ContextYear(root, course, year))
        self.adopt('issue', self.issue_context_class(root, course, year, self.target, issue))


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
    def __init__(self, root, course, lecture):
        super().__init__()
        self.load_meta(root, course, lecture)
        self.adopt('module', ContextSingleModule('scholar'))
        self.adopt('course', ContextSingleCourse(root, course))
        self.adopt('lecture', ContextSingleLecture(root, course, lecture))
        self.crawler = crawler.Crawler(Path(root, course, lecture))

        if 'parts' in self.data:
            self.add({'parts': [ContextScholarPart(root, course, lecture, part).data for part in self.data['parts']]})
        else:
            self.add_subdirs(ContextScholarPart, 'parts', root, course, lecture)


class ContextScholarPart(ContextScholarSingle):
    def __init__(self, root, course, lecture, part):
        super().__init__()
        self.load_meta(root, course, lecture, part) \
            .add_id(part)
        self.add_subdirs(ContextScholarProblem, 'problems', root, course, lecture, part)


class ContextScholarProblem(ContextScholarSingle):
    def __init__(self, root, course, lecture, part, problem):
        super().__init__()
        self.load_meta(root, course, lecture, part, problem) \
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
