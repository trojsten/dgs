import datetime
from schema import Schema, And, Optional

from .hierarchy import ContextIssue, ContextIssueSub, ContextIssueSubSub
from .buildable import ContextIssueBase


class HandoutMixin:
    target = 'handout'
    subdir = 'handouts'



class ContextHandoutProblem(HandoutMixin, ContextIssueSub):
    schema = Schema({
        'id': And(str, len),
    })

    def populate(self, course, year, issue, problem):
        self.add_id(problem)


class ContextHandoutIssue(HandoutMixin, ContextIssue):
    schema = Schema({
        'id': And(str, len),
        'number': int,
        'title': And(str, len),
        'date': datetime.date,
    })

    subcontext_key = 'problems'
    subcontext_class = ContextHandoutProblem


class ContextHandout(HandoutMixin, ContextIssueBase):
    schema = Schema({})

    issue_context_class = ContextHandoutIssue

