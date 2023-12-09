from pathlib import Path
from enschema import Schema

from core.builder import context
from core.builder.validator import String


class ContextI18n(context.FileSystemContext):
    _schema = Schema({
        'captions': {
            'problem': {
                'singular': String,
                'plural': String,
            },
            'solution': {
                'singular': String,
                'plural': String,
            },
        },
        'homework': {
            'title': String,
            'deadline': String,
            'disclaimer': {
                'foreword': String,
                'midword': String,
                'aftword': String,
            },
        },
        'handout': {
            'title': String,
        },
    })

    def populate(self, language):
        self.load_yaml('modules', 'scholar', 'i18n', language + '.yaml')

    def node_path(self, competition=None, language=None):
        return Path('modules', 'scholar', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.FileSystemContext):
    _schema = Schema({})

    def node_path(self):
        return Path('modules', 'scholar', 'i18n')

    def populate(self, course):
        for language in [x.stem for x in self.node_path().glob('*.yaml')]:
            self.adopt(language, ContextI18n(self.root, language))
