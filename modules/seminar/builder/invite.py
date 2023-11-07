import builder
import context


class BuilderInvite(builder.BuilderSemester):
    root_context_class = context.ContextInvite
    templates = [
        'invite.jtt',
    ]
    target = 'invite'


BuilderInvite().build()
