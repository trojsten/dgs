import builder
import context


class BuilderVolume(builder.BuilderVolume):
    root_context_class = context.ContextVolumeBooklet
    templates = [
        'intro.tex',
        'rules.tex',
    ]
    target = 'volume'


BuilderVolume().build()

