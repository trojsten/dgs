import builder
import context


class BuilderRound(builder.BuilderRound):
    root_context_class = context.ContextBooklet
    templates = {
        'templates': [
            'problems.tex',
            'solutions.tex',
        ],
    }
    target = 'round'


BuilderRound().build()
