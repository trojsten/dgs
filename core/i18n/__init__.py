import copy
import pprint
from pathlib import Path
from typing import Any, TextIO
from typing import Optional as Opt

import regex as re
import yaml
from enschema import Optional, Schema, SchemaMissingKeyError


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
        # Words that appear inside maths and have to be translated: `\QQText{and}` is `and` in
        # English and `a` in Slovak, and writing them out by hand is how the Spanish, Polish and
        # Portuguese solutions came to say `and`.
        #
        # `default.yaml` deliberately carries **no** `words:`. `merge()` would make whatever it
        # held the fallback for every language, and a fallback for prose means a Slovak booklet
        # printing `therefore` -- output that looks right until it is in print. A word this
        # language has not got is boxed in red instead, and collected for one report at the end of
        # the render; `core/audit`'s `word-missing` is what catches it from the sources.
        Optional('words'): dict[str, str],
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
        # csquotes has no style for every language we publish in, so a language may name
        # one; `fa` borrows English, whose marks are the ones it declares anyway.
        self.data['quotes'].setdefault('babel_id', self.full)
        self.locale = self.data['locale']
        self.name = self.data['full']
        self.rtl = self.data.get('rtl', False)

        try:
            self.schema.validate(self.as_dict())
        except SchemaMissingKeyError as exc:
            pprint.pprint(self.data)
            print(exc)
            raise

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

