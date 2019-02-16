import os
import base

class BuilderRound(base.BuilderSeminar):
    def __init__(self):
        self.rootContextClass   = base.ContextBooklet
        self.templates          = {
            'templates':    ['problems.tex', 'solutions.tex'],
        }
        self.target = 'round'
        super().__init__()

BuilderRound().build()
