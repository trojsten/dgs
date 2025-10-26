import yaml
import dotmap
import regex as re

from pathlib import Path
from typing import TextIO
from enschema import Schema, Optional


class Locale:
    def __init__(self, code, name, native_name, locale, quotes, siunitx: dict = None, *,
                 rtl=False, **extras):
        self.id = code
        self.name = name
        self.native_name = native_name
        self.locale = locale
        self.quotes = quotes
        self.quotes_extra = extras.get('quotes_extra', '')
        self.rtl = rtl
        self.figure = extras.get('figure', '<figure>')
        self.figures = extras.get('figures', '<figures>')
        self.table = extras.get('table', '<table>')
        self.tables = extras.get('tables', '<tables>')
        self.equation = extras.get('equation', '<equation>')
        self.equations = extras.get('equations', '<equations>')
        self.listing = extras.get('listing', '<listing>')
        self.listings = extras.get('listings', '<listings>')
        self.section = extras.get('section', '<section>')
        self.sections = extras.get('sections', '<sections>')

        if siunitx is None:
            siunitx = {}
        self.output_decimal_marker = siunitx.get('output_decimal_marker', '.')
        self.andw = siunitx.get('andw', '<and>')
        self.si_units = siunitx.get('units', {})
        self.si_prefixes = siunitx.get('prefixes', {})
        self.si_binary_prefixes = siunitx.get('prefixes', {})

    @staticmethod
    def load_yaml(file: TextIO):
        data = dotmap.DotMap(yaml.safe_load(file))
        match = re.search(r'core/i18n/(?P<lang>[a-z]{2})\.yaml$', file.name)

        return Locale(
            match.group('lang'),
            data.full,
            data.native,
            data.locale,
            (data.quotes.open, data.quotes.close),
        )

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'locale': self.locale,
            'quotes': {
                'open': self.quotes[0],
                'close': self.quotes[1],
                'babel_id': self.name,
                'extra': self.quotes_extra,
            },
            'rtl': self.rtl,
            'figure': self.figure,
            'figures': self.figures,
            'table': self.table,
            'tables': self.tables,
            'equation': self.equation,
            'equations': self.equations,
            'listing': self.listing,
            'listings': self.listings,
            'section': self.section,
            'sections': self.sections,
            'siunitx': {
                'andw': self.andw,
                'output_decimal_marker': self.output_decimal_marker,
                'list_final_separator': self.andw,
                'list_pair_separator': self.andw,
                'units': self.si_units,
                'prefixes': self.si_prefixes,
                'binary_prefixes': self.si_binary_prefixes,
            }
        }


LanguageSchema = Schema({
    'language': {
        'id': str,
        'name': str,
        'locale': str,
        'quotes': {
            'open': str,
            'close': str,
            'babel_id': str,
            Optional('extra'): str,
        },
        'figure': str,
        'figures': str,
        'table': str,
        'tables': str,
        'equation': str,
        'equations': str,
        Optional('listing'): str,
        Optional('listings'): str,
        Optional('section'): str,
        Optional('sections'): str,
        Optional('rtl', default=False): bool,
        'siunitx': {
            'list_pair_separator': str,
            'list_final_separator': str,
            'output_decimal_marker': str,
            Optional('units'): dict[str, str],
            Optional('prefixes'): dict[str, dict[str, str]],
            Optional('binary_prefixes'): dict[str, dict[str, str]],
        }
    }
})


languages = {}

for filename in Path('core/i18n').glob('*.yaml'):
    with open(filename, 'r') as file:
        locale = Locale.load_yaml(file)
        languages[locale.id] = locale


