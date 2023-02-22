from .base import ContextScholar
from .hierarchy import ContextIssue
from .buildable import ContextIssueBase


class HandoutMixin:
    target = 'handout'
    subdir = 'handouts'


class ContextHandoutSubproblem(HandoutMixin, ContextScholar):
    def populate(self, course, year, issue, problem, subproblem):
        self.load_meta(course, year, issue, problem, subproblem) \
            .add_id(subproblem)


class ContextHandoutProblem(HandoutMixin, ContextScholar):
    def populate(self, course, year, issue, problem):
        self.load_meta(course, year, issue, problem) \
            .add_id(sub)


class ContextHandoutIssue(HandoutMixin, ContextIssue):
    subcontext_name = 'problems'
    subcontext_class = ContextHandoutProblem


class ContextHandout(HandoutMixin, ContextIssueBase):
    issue_context_class = ContextHandoutIssue
