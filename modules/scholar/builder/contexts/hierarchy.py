from abc import ABCMeta

from enschema import And, Schema

from core.utilities.schema import valid_language

from .base import ContextScholar


class ContextCourse(ContextScholar):
    """
    The course, which is the top of the tree -- there is no year below it.

    `teacher:` sits here because the course meta is the only place left that can hold it: the
    year metas carried it while `TA1/2018` and `TA1/2025` were separate trees, and whoever is
    teaching the course now is a fact about the course. The documents print it once, in
    `homework-base.jtex`'s disclaimer.
    """
    _schema = Schema({
        'id': And(str, len),
        'title': And(str, len),
        'language': valid_language,
        'teacher': {
            'name': And(str, len),
            'email': And(str, len),
        },
    })

    def populate(self, course):
        self.load_meta(course) \
            .add_id(course)


class ContextIssue(ContextScholar, metaclass=ABCMeta):
    def populate(self, course, issue):
        self.load_meta(course, issue) \
            .add_id(f'{issue:02d}') \
            .add_number(issue)
        self.add_subdirs(course, issue)


class ContextIssueSub(ContextScholar):
    def populate(self, course, issue, sub):
        self.load_meta(course, issue, sub) \
            .add_id(sub)
        self.add_subdirs(course, issue, sub)


class ContextIssueSubSub(ContextScholar):
    def populate(self, course, issue, sub, subsub):
        self.load_meta(course, issue, sub, subsub) \
            .add_id(subsub)
