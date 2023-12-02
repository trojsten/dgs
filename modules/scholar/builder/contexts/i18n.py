import yaml
from pathlib import Path
from enschema import Schema

from core.builder import context
from core.utilities.schema import string


class ContextI18n(context.FileSystemContext):
    _schema = Schema({
        'captions': {
            'problem': {
                'singular': string,
                'plural': string,
            },
            'solution': {
                'singular': string,
                'plural': string,
            },
        },
        'homework': {
            'title': string,
            'deadline': string,
            'disclaimer': {
                'foreword': string,
                'midword': string,
                'aftword': string,
            },
        },
        'handout': {
            'title': string,
        },
        'crossref': {
            'tblPrefix': str,
            'figPrefix': str,
            'eqnPrefix': str,
            'figureTitle': str,
            'tableTitle': str,
        }
    })

    def populate(self, language):
        self.load_yaml('modules', 'scholar', 'i18n', language + '.yaml')
        contents = yaml.load(open(Path('core', 'i18n', language, 'crossref.yaml'), 'r'), Loader=yaml.SafeLoader)
        self.add({'crossref': contents})

    def node_path(self, competition=None, language=None):
        return Path('modules', 'scholar', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.FileSystemContext):
    _schema = Schema({})

    def node_path(self):
        return Path('modules', 'scholar', 'i18n')

    def populate(self, course):
        for language in [x.stem for x in self.node_path().glob('*.yaml')]:
            self.adopt(language, ContextI18n(self.root, language))
