from pathlib import Path
from schema import Schema

from core.builder import context


class ContextI18n(context.Context):
    schema = Schema({
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
        'physics_constants': {str: str},
    })

    def populate(self, root, competition, language):
        self.load_YAML(root, competition, '.static', 'i18n', language + '.yaml')


class ContextI18nGlobal(context.Context):
    schema = Schema({})

    def populate(self, root, competition):
        for language in [x.stem for x in Path(root, competition, '.static', 'i18n').glob('*.yaml')]:
            self.adopt(language, ContextI18n(root, competition, language))
