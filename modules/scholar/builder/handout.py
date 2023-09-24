from builder import BuilderScholar
from contexts import ContextHandout
from contexts.handout import HandoutMixin


class BuilderHandout(HandoutMixin, BuilderScholar):
    root_context_class = ContextHandout
    templates = [
        'handout-students.tex',
        'handout-solutions.tex',
        'handout-solved.tex',
    ]


BuilderHandout().build()
