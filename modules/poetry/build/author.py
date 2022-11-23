import builder
import context


class BuilderAuthor(builder.BuilderPoetry):
    target = 'author'
    root_context_class = context.ContextAuthor
    templates = ['author.tex']

    def id(self):
        return (self.args.author,)

    def path(self):
        return (self.args.author,)


BuilderAuthor().build()
