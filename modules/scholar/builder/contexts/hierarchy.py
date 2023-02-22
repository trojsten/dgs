from abc import ABCMeta
from schema import Schema, And

from .base import ContextScholar


class ContextCourse(ContextScholar):
    schema = Schema({
        'id': And(str, len),
        'title': And(str, len),
    })

    def populate(self, course):
        self.load_meta(course) \
            .add_id(course)


class ContextYear(ContextScholar):
    schema = Schema({
        'id': And(str, len),
        'number': int,
        'teacher': {
            'name': And(str, len),
            'email': And(str, len),
        }
    })

    def populate(self, course, year):
        self.load_meta(course, year) \
            .add_id(f'{year:04d}') \
            .add_number(year)


class ContextIssue(ContextScholar, metaclass=ABCMeta):
    def populate(self, course, year, issue):
        self.load_meta(course, year, issue) \
            .add_id(f'{issue:02d}') \
            .add_number(issue)
        self.add_subdirs(
            self.subcontext_class,
            self.subcontext_name,
            (course, year, issue),
            (course, year, issue),
        )


class ContextIssueSub(ContextScholar):
    def populate(self, course, year, issue, sub):
        self.load_meta(course, year, issue, sub) \
            .add_id(sub)
        self.add_subdirs(
            self.subcontext_class,
            self.subcontext_name,
            (course, year, issue, sub),
            (course, year, issue, sub),
        )


class ContextIssueSubSub(ContextScholar):
    def __init__(self, course, year, target, issue, sub, subsub):
        self.load_meta(course, year, target, issue, sub, subsub) \
            .add_id(subsub)
