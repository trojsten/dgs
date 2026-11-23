from modules.scholar import declaration
from modules.scholar.builder.builder import BuilderScholar
from modules.scholar.builder.contexts import ContextHandout, HandoutMixin


class BuilderHandout(HandoutMixin, BuilderScholar):
    _root_context_class = ContextHandout
    _node = declaration.HANDOUT


if __name__ == '__main__':
    BuilderHandout().build_templates()
