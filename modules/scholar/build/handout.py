import builder
import context


class BuilderHandout(builder.BuilderScholar):
    target = 'handout'
    subdir = 'handouts'

    root_context_class = context.ContextHandout
    templates = {
        'templates': [
            'handout-students.tex',
            'handout-solutions.tex',
        ],
    }


BuilderHandout().build()
