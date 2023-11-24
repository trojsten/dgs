from abc import ABCMeta

from core.builder.context import ContextModule, BuildableFilesystemContext
from .base import ContextScholar
from .hierarchy import ContextCourse, ContextYear
from .i18n import ContextI18n
from .validators import ScholarHomeworkValidator


class ContextIssueBase(BuildableFilesystemContext, ContextScholar, metaclass=ABCMeta):
    _issue_context_class = None
    _validator_class = ScholarHomeworkValidator

    def populate(self, course: str, year: int, issue: int):
        self.adopt('module', ContextModule('scholar'))
        self.adopt('course', ContextCourse(self.root, course))
        self.adopt('year', ContextYear(self.root, course, year))
        self.adopt('i18n', ContextI18n(self.root, self.data['course']['language']))
        self.adopt('issue', self._issue_context_class(self.root, course, year, issue))
