from modules.scholar.builder.builder import BuilderScholar
from modules.scholar.builder.contexts import ContextHandout, HandoutMixin


class BuilderHandout(HandoutMixin, BuilderScholar):
    _root_context_class = ContextHandout
    templates = [
        'handout-students.jtex',
        'handout-solutions.jtex',
        'handout-solved.jtex',
    ]


BuilderHandout().build_templates()
