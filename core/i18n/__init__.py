import yaml
import copy
import pprint
import regex as re

from pathlib import Path
from typing import TextIO, Optional as Opt, Any
from enschema import Schema, Optional, SchemaMissingKeyError


def merge(original, extras):
    output = copy.deepcopy(original)

    for key, value in extras.items():
        if isinstance(value, dict):
            if key in original:
                output[key] = merge(original[key], value)
            else:
                output[key] = value
        else:
            output[key] = value

    return output


class Locale:
    _ref_schema = Schema({
        'singular': str,
        'plural': str,
    })

    schema = Schema({
        'id': str,
        'full': str,
        'native': str,
        'locale': str,
        'quotes': {
            'open': str,
            'close': str,
            'babel_id': str,
            Optional('extra'): str,
        },
        'cref': {
            'figure': _ref_schema,
            'table': _ref_schema,
            'equation': _ref_schema,
            'listing': _ref_schema,
            'section': _ref_schema,
        },
        Optional('rtl', default=False): bool,
        'siunitx': {
            'list_pair_separator': str,
            'list_final_separator': str,
            'output_decimal_marker': str,
            'units': dict[str, str],
            'prefixes': dict[str, dict[str, str]],
            'binary_prefixes': dict[str, dict[str, str]],
        }
    })

    def __init__(self, code, **data):
        self.id = code
        self.data = data
        self.full = self.data['full']
        self.data['quotes']['babel_id'] = self.full
        self.locale = self.data['locale']
        self.name = self.data['full']
        self.rtl = self.data.get('rtl', False)

        try:
            self.schema.validate(self.as_dict())
        except SchemaMissingKeyError as exc:
            pprint.pprint(self.data)
            print(exc)
            raise exc

    @staticmethod
    def load_yaml(defaults: dict[str, Any], file: TextIO) -> Opt['Locale']:
        lang = yaml.safe_load(file)
        data = merge(defaults, lang)
        match = re.search(r'core/i18n/(?P<lang>[a-z]{2})\.yaml$', file.name)

        if match:
            return Locale(match.group('lang'), **data)
        else:
            return None

    def as_dict(self):
        out = {
            'id': self.id,
            'locale': self.locale,
            'rtl': self.rtl,
            'full': self.full,
        } | self.data
        return out



languages = {}

with open('core/i18n/default.yaml', 'r') as defaults_file:
    defaults = yaml.safe_load(defaults_file)

for filename in Path('core/i18n').glob('*.yaml'):
    with open(filename, 'r') as file:
        if (locale := Locale.load_yaml(defaults, file)) is not None:
            languages[locale.id] = locale

