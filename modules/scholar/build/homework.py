import os
import base

class BuilderHomework(base.BuilderScholar):
    target = 'homework'
    subdir = 'homework'

    def __init__(self):
        self.rootContextClass   = base.ContextHomework
        self.templates          = {
            'format':       ['format-course.tex', 'format-homework.tex'],
            'templates':    ['homework.tex'],
        }
        super().__init__()

BuilderHomework().build()
