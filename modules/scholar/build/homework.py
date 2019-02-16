import os
import base

class BuilderHomework(base.BuilderScholar):
    def __init__(self):
        self.rootContextClass   = base.ContextHomework
        self.templates          = {
            'format':       ['base.tex', 'homework.tex'],
            'templates':    ['homework.tex'],
        }
        self.target             = 'homework'
        super().__init__()

BuilderHomework().build()
