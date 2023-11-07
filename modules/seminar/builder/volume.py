import builder
import context


class BuilderVolume(builder.BuilderVolume):
    root_context_class = context.ContextVolumeBooklet
    templates = [
        'intro.jtt',
        'rules.jtt',
    ]
    target = 'volume'


BuilderVolume().build()

