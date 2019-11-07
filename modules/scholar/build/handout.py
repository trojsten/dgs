import builder
import context


class BuilderHandout(builder.BuilderScholar):
    target = 'handout'
    subdir = 'handouts'

    root_context_class = context.ContextHandout
    templates = {
        'format': [
            'format-course.tex',
            'format-handout.tex',
        ],
        'templates': [
            'handout-students.tex',
            'handout-solutions.tex',
        ],
    }


BuilderHandout().build()
