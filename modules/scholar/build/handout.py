import os
import base

class BuilderHandout(base.BuilderScholar):
    def __init__(self):
        self.rootContextClass   = base.ContextHandout
        self.templates          = {
            'format':       ['base.tex', 'handout.tex'],
            'templates':    ['handout.tex'],
        }
        self.target             = 'handout'
        super().__init__()

BuilderHandout().build()