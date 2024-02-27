from modules.seminar.builder import builder, context


class BuilderRound(builder.BuilderSeminar):
    _root_context_class = context.ContextBooklet
    _target = 'round'
    templates = [
        'problems.jtt',
        'solutions.jtt',
        'solutions-full.jtt',
        'instagram.jtt',
    ]


BuilderRound().build_templates()
