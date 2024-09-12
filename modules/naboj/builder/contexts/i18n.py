import yaml
from pathlib import Path
from enschema import Schema, Optional

from core.builder import context
from core.i18n import languages


class ContextI18n(context.FileSystemContext):
    _schema = Schema({
        'section': {
            'problems': str,
            'solutions': str,
            'answers': str,
            'modulo': str,
            'evaluators': str,
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
        'answers': {
            'interval': str,
            'also': str,
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
            str: str,
        },
        'globals': {
            'rtl': bool,
            'quotes': {
                'open': str,
                'close': str,
                'babel_id': str,
                Optional('extra'): str,
            },
            'siunitx': {
                'output_decimal_marker': str,
                'list_final_separator': str,
                'list_pair_separator': str,
            },
            str: str,
        },
    })

    def populate(self, competition, language):
        self.load_yaml(self.root, competition, '.static', 'i18n', language + '.yaml')
        self.add(globals=languages[language].as_dict())

    def node_path(self, competition=None, language=None):
        return Path(self.root, competition, '.static', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.FileSystemContext):
    _schema = Schema({})

    def node_path(self, competition):
        return Path(self.root, competition, '.static', 'i18n')

    def populate(self, competition):
        self.adopt(**{
            language: ContextI18n(self.root, competition, language)
            for language in [x.stem for x in self.node_path(competition).glob('*.yaml')]
        })
