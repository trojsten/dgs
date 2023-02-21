import os
import sys
import collections
from pathlib import Path
from abc import ABCMeta, abstractmethod

sys.path.append('.')

from core.builder.context import Context, BuildableContext
from core.utils import crawler



# Homework and its subcontexts


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
