import builder
import context
from core.utilities import crawler


class BuilderLecture(builder.BuilderSingle):
    target = 'lecture'

    root_context_class = context.ContextScholarLecture
    templates = [
        'lecture.tex',
    ]


BuilderLecture().build()
