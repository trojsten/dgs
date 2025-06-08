import logging

from modules.seminar.builder import builder, context

log = logging.getLogger('dgs')


class BuilderRound(builder.BuilderSeminar):
    _root_context_class = context.ContextBooklet
    _target = 'round'
    templates = [
        'problems.jinja.tex',
        'solutions.jinja.tex',
        'solutions-full.jinja.tex',
        'instagram.jinja.tex',
    ]


BuilderRound().build_templates()
