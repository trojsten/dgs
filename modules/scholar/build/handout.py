import os
import base

class BuilderHandout(base.BuilderScholar):
    target = 'handout'
    subdir = 'handouts'

    def __init__(self):
        self.rootContextClass   = base.ContextHandout
        self.templates          = {
            'format':       ['format-course.tex', 'format-handout.tex'],
            'templates':    ['handout-students.tex', 'handout-solutions.tex'],
        }
        super().__init__()

BuilderHandout().build()
