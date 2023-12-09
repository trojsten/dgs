import sys
from pathlib import Path

sys.path.append('.')

from core.builder.context import FileSystemContext, BuildableFileSystemContext
from core.utilities import crawler


class ContextScholarSingle(BuildableFileSystemContext):
    @staticmethod
    def node_path(root, course='', lecture='', part='', problem=''):
        return Path(root, course, lecture, part, problem)


class ContextScholarLecture(ContextScholarSingle):
    def populate(self, course, lecture):
        self.load_meta(course, lecture)
        self.adopt('module', ContextSingleModule(self.root, 'scholar'))
        self.adopt('course', ContextSingleCourse(self.root, course))
        self.adopt('lecture', ContextSingleLecture(self.root, course, lecture))

        if 'parts' in self.data:
            self.add({'parts': [
                ContextScholarPart(self.root, course, lecture, part).data for part in self.data['parts']
            ]})
        else:
            self.add_subdirs(ContextScholarPart, 'parts', self.root, course, lecture)


class ContextScholarPart(ContextScholarSingle):
    def populate(self, course, lecture, part):
        self.name(course, lecture, part)
        self.load_meta(course, lecture, part) \
            .add_id(part)
        self.add_subdirs(ContextScholarProblem, 'problems', self.root, course, lecture, part)


class ContextScholarProblem(ContextScholarSingle):
    def populate(self, course, lecture, part, problem):
        self.name(course, lecture, part, problem)
        self.load_meta(course, lecture, part, problem) \
            .add_id(problem)
        self.add({'has_problem': Path(self.root, course, lecture, part, problem, 'problem.md').is_file()})
        self.add({'has_solution': Path(self.root, course, lecture, part, problem, 'solution.md').is_file()})


class ContextSingleModule(ContextScholarSingle):
    def populate(self, root, module):
        self.add_id(module)


class ContextSingleCourse(ContextScholarSingle):
    def populate(self, root, course):
        self.load_meta(root, course).add_id(course)


class ContextSingleLecture(ContextScholarSingle):
    def populate(self, root, course, lecture):
        self.load_meta(root, course, lecture).add_id(lecture)
        self.add({'has_abstract': Path(root, course, lecture, 'abstract.md').is_file()})


class ContextDir(FileSystemContext):
    def populate(self, root, *deeper):
        self.load_meta(root, *deeper) \
            .add_id(deeper[-1] if deeper else root)

        crawl = crawler.Crawler(Path(root, *deeper))
        self.add({'children': ContextDir(root, *deeper, child).data for child in crawl.children()})

    @staticmethod
    def node_path(*args):
        return Path(*args)
