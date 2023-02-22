from .hierarchy import ContextIssue, ContextIssueSub, ContextIssueSubSub
from .buildable import ContextIssueBase


class HandoutMixin:
    target = 'handout'
    subdir = 'handouts'



class ContextHandoutProblem(HandoutMixin, ContextIssueSub):
    def populate(self, course, year, issue, problem):
        self.add_id(problem)


class ContextHandoutIssue(HandoutMixin, ContextIssue):
    arg_schema = (str, int, int)
    subcontext_key = 'problems'
    subcontext_class = ContextHandoutProblem


class ContextHandout(HandoutMixin, ContextIssueBase):
    arg_schema = (str, int, int)
    issue_context_class = ContextHandoutIssue


