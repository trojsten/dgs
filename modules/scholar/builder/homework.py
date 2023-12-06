from builder import BuilderScholar
from contexts import ContextHomework
from contexts.homework import HomeworkMixin


class BuilderHomework(HomeworkMixin, BuilderScholar):
    _root_context_class = ContextHomework
    templates = [
        'homework-students.jtt',
        'homework-solutions.jtt',
    ]


BuilderHomework().build_templates()
