import logging

from modules.seminar.builder import builder, context

log = logging.getLogger('dgs')


class BuilderRound(builder.BuilderSeminar):
    _root_context_class = context.ContextBooklet
    _target = 'round'
    templates = [
        'problems.jtex',
        'solutions.jtex',
        'solutions-full.jtex',
        'instagram.jtex',
    ]


BuilderRound().build_templates()
