import datetime
from enschema import Schema, And

from .hierarchy import ContextIssue, ContextIssueSub
from .buildable import ContextIssueBase
from .validators import HandoutValidator


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
    _validator_class = HandoutValidator
    _issue_context_class = ContextHandoutIssue
