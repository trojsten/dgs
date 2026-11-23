import logging

from core.builder.jinja import StaticRenderer
from modules.seminar import declaration
from modules.seminar.builder import builder, context

log = logging.getLogger('dgs')


class BuilderRound(builder.BuilderSeminar):
    _root_context_class = context.ContextBooklet
    _target = 'round'

    _renderer_class = StaticRenderer
    _node = declaration.ROUND


if __name__ == '__main__':
    BuilderRound().build_templates()
