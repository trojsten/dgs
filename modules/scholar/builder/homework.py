from modules.scholar.builder.builder import BuilderScholar
from modules.scholar.builder.contexts import ContextHomework, HomeworkMixin


class BuilderHomework(HomeworkMixin, BuilderScholar):
    _root_context_class = ContextHomework
    templates = [
        'homework-students.jtex',
        'homework-solutions.jtex',
    ]


BuilderHomework().build_templates()
