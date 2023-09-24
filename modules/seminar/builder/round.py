import builder
import context


class BuilderRound(builder.BuilderRound):
    root_context_class = context.ContextBooklet
    templates = [
        'problems.tex',
        'solutions.tex',
        'solutions-full.tex',
        'instagram.tex',
    ]
    target = 'round'


BuilderRound().build()
