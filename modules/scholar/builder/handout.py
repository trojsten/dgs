import builder
import contexts


class BuilderHandout(builder.BuilderScholar):
    target = 'handout'
    subdir = 'handouts'

    root_context_class = contexts.ContextHandout
    templates = [
        'handout-students.tex',
        'handout-solutions.tex',
    ]


BuilderHandout().build()
