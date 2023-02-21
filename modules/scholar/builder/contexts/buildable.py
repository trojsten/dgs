from core.builder.context import ContextModule, BuildableContext
from .base import ContextScholar
from .hierarchy import ContextCourse, ContextYear


class ContextIssueBase(BuildableContext, ContextScholar):
    def populate(self, course: str, year: int, issue: int):
        self.adopt('module', ContextModule('scholar'))
        self.adopt('course', ContextCourse(self.root, course))
        self.adopt('year', ContextYear(self.root, course, year))
        self.adopt('issue', self.issue_context_class(self.root, course, year, issue))

