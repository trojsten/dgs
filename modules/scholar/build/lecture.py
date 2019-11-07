import builder
import context


class BuilderLecture(builder.BuilderSingle):
    target = 'lecture'

    rootContextClass = context.ContextScholarLecture
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
