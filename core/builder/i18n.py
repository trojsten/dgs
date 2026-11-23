from core import i18n
from core.builder import declaration
from core.builder.builder import BaseBuilder
from core.builder.context.buildable import BuildableContext
from core.builder.jinja import StaticRenderer


class BuildableContextCoreI18n(BuildableContext):
    def __init__(self, root, language):
        super().__init__(language)
        self.populate(language)

    def populate(self, language):
        self._data = {'i18n': i18n.languages[language].as_dict()}
        self.add_id(language)


class BuilderI18n(BaseBuilder):
    module = 'core'
    _target = 'global i18n'
    _root_context_class = BuildableContextCoreI18n
    _renderer_class = StaticRenderer

    _node = declaration.I18N

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('language', type=str, choices=i18n.languages.keys())

    def ident(self) -> tuple:
        return self.args.language,

    def path(self) -> tuple:
        return self.ident()

    def product_ident(self) -> str:
        """Both products are named after the language, not after their templates."""
        return self.args.language


if __name__ == '__main__':
    BuilderI18n().build_templates()
