from .hierarchy import ContextIssue, ContextIssueSub, ContextIssueSubSub
from .buildable import ContextIssueBase


class ContextHomeworkProblem(ContextIssueSub):
    subcontext_name = 'subproblems'
    subcontext_class = ContextIssueSubSub


class ContextHomeworkIssue(ContextIssue):
    subcontext_name = 'problems'
    subcontext_class = ContextHomeworkProblem


class ContextHomework(ContextIssueBase):
    target = 'homework'
    subdir = 'homework'
    issue_context_class = ContextHomeworkIssue
