from pathlib import Path
from schema import Schema

from core.builder import context


class ContextI18n(context.FileSystemContext):
    _schema = Schema({
        'section': {
            'problems': str,
            'solutions': str,
            'answers': str,
            'modulo': str,
        },
        'caption': {
            'table': str,
            'figure': str,
        },
        'competition': {
            'name': {
                'nominative': str,
                'genitive': str,
            },
            'email': str,
            'website': str,
        },
        'envelope': {
            'donotopen': str,
        },
        'constants': {
            'title': str,
            'instruction': str,
            'constant': str,
            'symbol': str,
            'value': str,
        },
        'tearoff': {
            'team': str,
            'bottom': str,
        },
        'instructions': {
            'title': str,
        },
        'instructions_online': {
            'title': str,
        },
        'physics_constants': {
            str: str
        },
    })

    def populate(self, competition, language):
        self.load_yaml(self.root, competition, '.static', 'i18n', language + '.yaml')

    def node_path(self, competition=None, language=None):
        return Path(self.root, competition, '.static', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.FileSystemContext):
    _schema = Schema({})

    def node_path(self, competition):
        return Path(self.root, competition, '.static', 'i18n')

    def populate(self, competition):
        for language in [x.stem for x in self.node_path(competition).glob('*.yaml')]:
            self.adopt(language, ContextI18n(self.root, competition, language))
