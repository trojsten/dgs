from enschema import Schema, Optional


class Locale:
    def __init__(self, code, name, locale, quotes, *,
                 rtl=False, **extras):
        self.id = code
        self.name = name
        self.locale = locale
        self.quotes = quotes
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
        self.andw = extras.get('andw', '<and>')
        self.output_decimal_marker = extras.get('output_decimal_marker', '.')

        self.quotes_extra = extras.get('quotes_extra', '')

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
            }
        }


languages = [
    Locale('sk', 'slovak', 'sk-SK', ('„', '“'),
           figure='obrázok', figures='obrázky',
           table='tabuľka', tables='tabuľky',
           equation='rovnica', equations='rovnice',
           section='úloha', sections='úlohy',
           andw='a',
           output_decimal_marker=','),
    Locale('en', 'english', 'en-US', ('“', '”'),
           figure='figure', figures='figures',
           table='table', tables='tables',
           equation='equation', equations='equations',
           section='problem', sections='problems',
           andw='and'),
    Locale('cs', 'czech', 'cs-CZ', ('„', '“'),
           figure='obrázek', figures='obrázky',
           table='tabulka', tables='tabulky',
           equation='rovnice', equations='rovnice',
           section='problém', sections='problémy',
           andw='a',
           output_decimal_marker=',',
    ),
    Locale('ru', 'russian', 'ru-RU', ('«', '»'),
           figure='фигура', figures='фигуры',
           table='таблица', tables='таблицы',
           equation='уравнение', equations='уравнения'),
    Locale('de', 'german', 'de-AT', ('„', '“'),
           figure='abbildung', figures='abbildungen',
           table='tabelle', tables='tabellen',
           equation='gleichung', equations='gleichungen',
           andw='und',
           output_decimal_marker=','),
    Locale('pl', 'polish', 'pl-PL', ('„', '“'),
           figure='figura', figures='figury',
           table='tabela', tables='tabely',
           equation='równanie', equations='równania',
           andw='i',
           output_decimal_marker=',',
    ),
    Locale('hu', 'hungarian', 'hu-HU', ('„', '“'),
           figure='ábra', figures='ábrák',
           table='táblázat', tables='táblázatok',
           equation='egyenlet', equations='egyenletek',
           andw='és',
           output_decimal_marker=',',
    ),
    Locale('fr', 'french', 'fr-FR', ('«\u202F', '\u202F»'),
           figure='figure', figures='figures',
           table='tableau', tables='tableaux',
           equation='équation', equations='équations',
           andw='et'),
    Locale('es', 'spanish', 'es-ES', ('«', '»'),
           figure='figura', figures='figuras',
           table='tabla', tables='tables',
           equation='ecuación', equations='ecuacións',
           andw='y'),
    Locale('fa', 'farsi', 'en-US', ('“', '”'),              ### This one is not correct but
           figure='figure', figures='figures',              ### must be present for validation
           table='table', tables='tables',
           equation='equation', equations='equations',
           section='section', sections='sections'),
    Locale('qq', 'test', 'sk-SK', ('(', ')'),
           figure='obrázok', figures='obrázky',
           table='tabuľka', tables='tabuľky',
           equation='rovnica', equations='rovnice'),
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
        'andw': str,
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
        }
    }
})
