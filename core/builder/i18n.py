import sys
from pathlib import Path

sys.path.append('.')

from core.builder.builder import BaseBuilder
from core.builder.context import BuildableFilesystemContext, BuildableContext

from core import i18n


class BuildableContextCoreI18n(BuildableContext):
    def __init__(self, root, language):
        super().__init__(root, language)
        self.populate(language)

    def populate(self, language):
        self.data = {'i18n': i18n.languages[language].as_dict()}
        self.add_id(language)


class BuilderI18n(BaseBuilder):
    module = 'core'
    _target = 'global i18n'
    _root_context_class = BuildableContextCoreI18n

    templates = ['override.jtt']

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('language', type=str, choices=i18n.languages.keys())

    def id(self) -> tuple:
        return self.args.language,

    def path(self) -> tuple:
        return self.id()

    def build_templates(self, *, new_name: str = None):
        super().build_templates(new_name=self.args.language)

b = BuilderI18n()
b.build_templates()
