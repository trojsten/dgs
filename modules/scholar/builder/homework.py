import builder
import context


class BuilderHomework(builder.BuilderScholar):
    target = 'homework'
    subdir = 'homework'

    root_context_class = context.ContextHomework
    templates = [
        'homework-students.tex',
        'homework-solutions.tex',
    ]


BuilderHomework().build()
