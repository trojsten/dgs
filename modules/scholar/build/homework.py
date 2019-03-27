import os
import base

class BuilderHomework(base.BuilderScholar):
    target = 'homework'
    subdir = 'homework'

    rootContextClass   = base.ContextHomework
    templates          = {
        'format':       ['format-course.tex', 'format-homework.tex'],
        'templates':    ['homework.tex'],
    }

BuilderHomework().build()
