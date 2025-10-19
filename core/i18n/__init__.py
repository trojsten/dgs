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
            'andw': self.andw,
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
                'output_decimal_marker': self.output_decimal_marker,
                'list_final_separator': self.andw,
                'list_pair_separator': self.andw,
                'units': self.si_units,
                'prefixes': self.si_prefixes,
                'binary_prefixes': self.si_binary_prefixes,
            }
        }


languages = [
    Locale('sk', 'slovak', 'slovensky', 'sk-SK', ('„', '“'),
           figure='obrázok', figures='obrázky',
           table='tabuľka', tables='tabuľky',
           equation='rovnica', equations='rovnice',
           section='úloha', sections='úlohy',
           siunitx=dict(
               andw='a',
               output_decimal_marker=','
           )),
    Locale('en', 'english', 'English', 'en-US', ('“', '”'),
           figure='figure', figures='figures',
           table='table', tables='tables',
           equation='equation', equations='equations',
           section='problem', sections='problems',
           siunitx=dict(
               andw='and',
           )),
    Locale('cs', 'czech', 'česky', 'cs-CZ', ('„', '“'),
           figure='obrázek', figures='obrázky',
           table='tabulka', tables='tabulky',
           equation='rovnice', equations='rovnice',
           section='problém', sections='problémy',
           siunitx=dict(
               andw='a',
               output_decimal_marker=','
           )),
    Locale('ru', 'russian', 'русский', 'ru-RU', ('«', '»'),
           figure='фигура', figures='фигуры',
           table='таблица', tables='таблицы',
           equation='уравнение', equations='уравнения'),
    Locale('de', 'german', 'deutsch', 'de-AT', ('„', '“'),
           figure='Abbildung', figures='Abbildungen',
           table='Tabelle', tables='Tabellen',
           equation='Gleichung', equations='Gleichungen',
           siunitx=dict(
               andw='und',
               output_decimal_marker=',',
           )),
    Locale('pl', 'polish', 'polski', 'pl-PL', ('„', '“'),
           figure='figura', figures='figury',
           table='tabela', tables='tabely',
           equation='równanie', equations='równania',
           siunitx=dict(
               andw='i',
               output_decimal_marker=',',
           )),
    Locale('hu', 'hungarian', 'magyar', 'hu-HU', ('„', '“'),
           figure='ábra', figures='ábrák',
           table='táblázat', tables='táblázatok',
           equation='egyenlet', equations='egyenletek',
           siunitx=dict(
               andw='és',
               output_decimal_marker=',',
           )),
    Locale('fr', 'french', 'fr-FR', 'français', ('«\u202F', '\u202F»'),
           figure='figure', figures='figures',
           table='tableau', tables='tableaux',
           equation='équation', equations='équations',
           siunitx=dict(
               andw='et',
           )),
    Locale('es', 'spanish', 'es-ES', 'español', ('«', '»'),
           figure='figura', figures='figuras',
           table='tabla', tables='tables',
           equation='ecuación', equations='ecuacións',
           siunitx=dict(
               andw='y',
           )),
    Locale('fa', 'farsi', 'en-US', 'farsi', ('“', '”'),              ### This one is not correct but
           figure='figure', figures='figures',              ### must be present for validation
           table='table', tables='tables',
           equation='equation', equations='equations',
           section='section', sections='sections'),
    Locale('qq', 'test', 'sk-SK', 'quot-test', ('(', ')'),
           figure='obrázok', figures='obrázky',
           table='tabuľka', tables='tabuľky',
           equation='rovnica', equations='rovnice'),
    Locale('uk', 'ukrainian', 'uk-UK', 'українська', ('«', '»'),
           figure="Figure", figures="Figures",
           table="Table", tables="Tables",
           equation="Equation", equations="Equations",
           siunitx=dict(
               andw="і",
               output_decimal_marker=',',
               units={
                   'metre': 'м',
                   'meter': 'м',
                   'second': 'с',
                   'ampere': 'А',
                   'kelvin': 'К',
                   'mole': 'моль',
                   'candela': 'кд',
                   'becquerel': 'Бк',
                   'coulomb': 'Кл',
                   'farad': 'Ф',
                   'gram': 'г',
                   'gray': 'Гр',
                   'hertz': 'Гц',
                   'henry': 'Гн',
                   'joule': 'Дж',
                   'katal': 'кат',
                   'lumen': 'лм',
                   'lux': 'лк',
                   'newton': 'Н',
                   'ohm': 'Ом',
                   'pascal': 'Па',
                   'radian': 'рад',
                   'siemens': 'См',
                   'sievert': 'Зв',
                   'steradian': 'ср',
                   'tesla': 'Тл',
                   'volt': 'В',
                   'watt': 'Вт',
                   'weber': 'Вб',

                   'day': 'сут',
                   'hectare': 'га',
                   'hour': 'ч',
                   'litre': 'л',
                   'liter': 'л',
                   'minute': 'мин',
                   'tonne': 'т',

                   'astronomicalunit': 'а. е.',
                   'atomicmassunit': 'а. е. м.',
                   'dalton': 'а. е. м.',
                   'electronvolt': 'эВ',
                   'bar': 'бар',
                   'barn': 'б',
                   'bel': 'Б',
                   'decibel': 'дБ',
                   'knot': 'уз',
                   'mmHg': 'мм рт. ст.',
                   'nauticalmile': 'миля',
                   'neper': 'Нп',
               },
               prefixes={
                   1: {'name': 'deca', 'symbol': 'да'},
                   2: {'name': 'hecto', 'symbol': 'г'},
                   3: {'name': 'kilo', 'symbol': 'к'},
                   6: {'name': 'mega', 'symbol': 'М'},
                   9: {'name': 'giga', 'symbol': 'Г'},
                   12: {'name': 'tera', 'symbol': 'Т'},
                   15: {'name': 'peta', 'symbol': 'П'},
                   18: {'name': 'exa', 'symbol': 'Э'},
                   21: {'name': 'zetta', 'symbol': 'З'},
                   24: {'name': 'yotta', 'symbol': 'И'},
                   -1: {'name': 'deci', 'symbol': 'д'},
                   -2: {'name': 'centi', 'symbol': 'с'},
                   -3: {'name': 'milli', 'symbol': 'м'},
                   -6: {'name': 'micro', 'symbol': 'мк'},
                   -9: {'name': 'nano', 'symbol': 'н'},
                   -12: {'name': 'pico', 'symbol': 'п'},
                   -15: {'name': 'femto', 'symbol': 'ф'},
                   -18: {'name': 'atto', 'symbol': 'а'},
                   -21: {'name': 'zepto', 'symbol': 'з'},
                   -24: {'name': 'yocto', 'symbol': 'и'},
               },
               binary_prefixes={
                   10: {'name': 'kibi', 'symbol': 'Ки'},
                   20: {'name': 'mebi', 'symbol': 'Ми'},
                   30: {'name': 'gibi', 'symbol': 'Ги'},
                   40: {'name': 'tebi', 'symbol': 'Ти'},
                   50: {'name': 'pebi', 'symbol': 'Пи'},
                   60: {'name': 'exbi', 'symbol': 'Эи'},
                   70: {'name': 'zebi', 'symbol': 'Зи'},
                   80: {'name': 'yobi', 'symbol': 'Йи'},
               },
           )
        ),
    Locale('pt', 'portuguese', 'pt-PT', 'português ', ('«', '»'),
           figure='figura', figures='figuras',
           table='tabla', tables='tables',
           equation='ecuación', equations='ecuacións',
           siunitx=dict(
               andw='y',
           )),
]

languages = {locale.id: locale for locale in languages}

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
