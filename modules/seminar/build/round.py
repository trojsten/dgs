import os
import base
import core.utilities.jinja as jinja
import core.utilities.colour as c

class BuilderRound(base.BuilderSeminar):
    def __init__(self):
        super().__init__(
            base.ContextBooklet,
            templates       = ['problems.tex', 'solutions.tex'],
            templateRoot    = os.path.dirname(os.path.dirname(__file__)),
        )
        self.target = 'round'

builder = BuilderRound()
builder.debugInfo()
builder.build()
