import os
import base

class BuilderHandout(base.BuilderScholar):
    def __init__(self):
        super().__init__(
            base.ContextHandout,
            formatters      = ['format-handout.tex'],
            templates       = ['handout.tex'],
            templateRoot    = os.path.dirname(os.path.dirname(__file__)),
        )
        self.target = 'handout'

builder = BuilderHandout()
builder.debugInfo()
builder.build()
