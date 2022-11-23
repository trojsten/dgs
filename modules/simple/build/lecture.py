import builder
import context


class BuilderLecture(builder.BuilderSingle):
    target = 'lecture'

    root_context_class = context.ContextScholarLecture
    templates = {
        'format': [
            'format-course.tex',
            'format-lecture.tex',
        ],
        'templates': [
            'lecture.tex',
        ],
    }


BuilderLecture().build()
