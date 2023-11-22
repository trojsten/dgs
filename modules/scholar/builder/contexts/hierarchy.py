from abc import ABCMeta
from schema import Schema, And

from .base import ContextScholar

from core.utilities.schema import valid_language


class ContextCourse(ContextScholar):
    _schema = Schema({
        'id': And(str, len),
        'title': And(str, len),
        'language': valid_language
    })

    def populate(self, course):
        self.load_meta(course) \
            .add_id(course)


class ContextYear(ContextScholar):
    _schema = Schema({
        'id': And(str, len),
        'number': int,
        'teacher': {
            'name': And(str, len),
            'email': And(str, len),
        }
    })

    def populate(self, course: str, year: int):
        self.load_meta(course, year) \
            .add_id(f'{year:04d}') \
            .add_number(year)


class ContextIssue(ContextScholar, metaclass=ABCMeta):
    def populate(self, course, year, issue):
        self.load_meta(course, year, issue) \
            .add_id(f'{issue:02d}') \
            .add_number(issue)
        self.add_subdirs(course, year, issue)


class ContextIssueSub(ContextScholar):
    def populate(self, course, year, issue, sub):
        self.load_meta(course, year, issue, sub) \
            .add_id(sub)
        self.add_subdirs(course, year, issue, sub)


class ContextIssueSubSub(ContextScholar):
    def populate(self, course, year, issue, sub, subsub):
        self.load_meta(course, year, issue, sub, subsub) \
            .add_id(subsub)
