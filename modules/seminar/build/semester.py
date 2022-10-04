import builder
import context


class BuilderSemester(builder.BuilderSemester):
    root_context_class = context.ContextSemesterBooklet
    templates = [
        'semester.tex',
    ]
    target = 'semester'


BuilderSemester().build()

