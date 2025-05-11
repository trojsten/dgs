import logging

from core.utilities import logger
from modules.seminar.builder import builder, context

log = logging.getLogger('dgs')


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
