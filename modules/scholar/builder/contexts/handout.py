import datetime
from schema import And

from core.utilities.schema import Schema
from .hierarchy import ContextIssue, ContextIssueSub
from .buildable import ContextIssueBase


class HandoutMixin:
    _target = 'handout'
    _subdir = 'handouts'


class ContextHandoutProblem(HandoutMixin, ContextIssueSub):
    _schema = Schema({
        'id': And(str, len),
    })

    def populate(self, course, year, issue, problem):
        self.add_id(problem)


class ContextHandoutIssue(HandoutMixin, ContextIssue):
    _schema = Schema({
        'id': And(str, len),
        'number': int,
        'title': And(str, len),
        'date': datetime.date,
    })

    _subcontext_key = 'problems'
    _subcontext_class = ContextHandoutProblem


class ContextHandout(HandoutMixin, ContextIssueBase):
    _schema = Schema({})

    _issue_context_class = ContextHandoutIssue
