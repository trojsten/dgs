from abc import ABCMeta

from core.builder.context import BuildableFileSystemTreeContext, ContextModule

from .base import ContextScholar
from .hierarchy import ContextCourse
from .i18n import ContextI18n


class ContextIssueBase(BuildableFileSystemTreeContext, ContextScholar, metaclass=ABCMeta):
    _issue_context_class = None

    def populate(self, course: str, issue: int):
        self.adopt(
            module=ContextModule('scholar'),
            course=ContextCourse(self.root, course),
            issue=self._issue_context_class(self.root, course, issue),
        ).adopt(
            i18n=ContextI18n(self.root, self.data['course']['language']),
        )
