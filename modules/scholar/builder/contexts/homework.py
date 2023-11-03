import datetime
from schema import Schema, And, Optional

from .hierarchy import ContextIssue, ContextIssueSub, ContextIssueSubSub
from .buildable import ContextIssueBase


class HomeworkMixin:
    target = 'homework'
    subdir = 'homework'


class ContextHomeworkSubproblem(HomeworkMixin, ContextIssueSubSub):
    _schema = Schema({
        'id': And(str, len),
        'name': And(str, len),
        Optional('bonus'): bool,
    })


class ContextHomeworkProblem(HomeworkMixin, ContextIssueSub):
    subcontext_key = 'subproblems'
    subcontext_class = ContextHomeworkSubproblem
    _schema = Schema({
        'id': And(str, len),
        'name': And(str, len),
        Optional('bonus'): bool,
    })


class ContextHomeworkIssue(HomeworkMixin, ContextIssue):
    subcontext_key = 'problems'
    subcontext_class = ContextHomeworkProblem
    _schema = Schema({
        'deadline': datetime.date,
        'id': And(str, len),
        'number': int,
    })


class ContextHomework(HomeworkMixin, ContextIssueBase):
    issue_context_class = ContextHomeworkIssue
    _schema = Schema({})
