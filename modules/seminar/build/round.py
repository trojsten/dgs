import os
import base

class BuilderRound(base.BuilderSeminar):
    rootContextClass   = base.ContextBooklet
    templates          = {
        'templates':    ['problems.tex', 'solutions.tex'],
    }
    target = 'round'

BuilderRound().build()
