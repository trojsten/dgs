import os
import base

class BuilderLecture(base.BuilderSingle):
    target = 'lecture'

    rootContextClass   = base.ContextScholarLecture
    templates          = {
        'format':       ['format-course.tex', 'format-lecture.tex'],
        'templates':    ['lecture.tex'],
    }

BuilderLecture().build()
