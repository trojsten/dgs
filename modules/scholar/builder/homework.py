import builder
from contexts import ContextHomework


class BuilderHomework(builder.BuilderScholar):
    target = 'homework'
    subdir = 'homework'

    root_context_class = ContextHomework
    templates = [
        'homework-students.tex',
        'homework-solutions.tex',
    ]


BuilderHomework().build()
