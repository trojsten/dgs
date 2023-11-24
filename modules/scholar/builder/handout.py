from builder import BuilderScholar
from contexts import ContextHandout
from contexts.handout import HandoutMixin


class BuilderHandout(HandoutMixin, BuilderScholar):
    _root_context_class = ContextHandout
    templates = [
        'handout-students.jtt',
        'handout-solutions.jtt',
        'handout-solved.jtt',
    ]


BuilderHandout().build()
