from .base import ContextScholar
from .hierarchy import ContextIssue
from .buildable import ContextIssueBase


class ContextHandoutSubSub(ContextScholar):
    def __init__(self, course, year, target, issue, sub, subsub):
        super().__init__()
        self.add_id(subsub)


class ContextHandoutProblem(ContextScholar):
    def populate(self, course, year, target, issue, sub):
        self.name(course, year, target, issue, sub)
        self.add_id(sub)


class ContextHandoutIssue(ContextIssue):
    subcontext_name = 'problems'
    subcontext_class = ContextHandoutProblem


class ContextHandout(ContextIssueBase):
    issue_context_class = ContextHandoutIssue
    target = 'handout'
    subdir = 'handouts'
