from modules.seminar.builder import builder, context


class BuilderVolume(builder.BuilderSeminar):
    _root_context_class = context.ContextVolumeBooklet
    templates = [
        'intro.jtt',
        'rules.jtt',
    ]
    _target = 'volume'


BuilderVolume().build_templates()
