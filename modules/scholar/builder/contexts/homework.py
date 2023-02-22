from .hierarchy import ContextIssue, ContextIssueSub, ContextIssueSubSub
from .buildable import ContextIssueBase


class HomeworkMixin:
    target = 'homework'
    subdir = 'homework'


class ContextHomeworkSubproblem(HomeworkMixin, ContextIssueSubSub):
    pass


class ContextHomeworkProblem(HomeworkMixin, ContextIssueSub):
    subcontext_key = 'subproblems'
    subcontext_class = ContextHomeworkSubproblem


class ContextHomeworkIssue(HomeworkMixin, ContextIssue):
    subcontext_key = 'problems'
    subcontext_class = ContextHomeworkProblem


class ContextHomework(HomeworkMixin, ContextIssueBase):
    issue_context_class = ContextHomeworkIssue

    def node_path(self, course, year, issue):
        return super()
