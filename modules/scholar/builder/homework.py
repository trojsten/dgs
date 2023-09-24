from builder import BuilderScholar
from contexts import ContextHomework
from contexts.homework import HomeworkMixin


class BuilderHomework(HomeworkMixin, BuilderScholar):
    root_context_class = ContextHomework
    templates = [
        'homework-students.tex',
        'homework-solutions.tex',
    ]


BuilderHomework().build()
