from modules.scholar import declaration
from modules.scholar.builder.builder import BuilderScholar
from modules.scholar.builder.contexts import ContextHomework, HomeworkMixin


class BuilderHomework(HomeworkMixin, BuilderScholar):
    _root_context_class = ContextHomework
    _node = declaration.HOMEWORK


if __name__ == '__main__':
    BuilderHomework().build_templates()
