from enschema import Schema, Optional


class Locale:
    def __init__(self, code, name, locale, quotes, *,
                 rtl=False, **extras):
        self.id = code
        self.name = name
        self.locale = locale
        self.quotes = quotes
        self.rtl = rtl
        self.figure = extras.get('figure', '??')
        self.figures = extras.get('figures', '??')
        self.table = extras.get('table', '??')
        self.tables = extras.get('tables', '??')
        self.equation = extras.get('equation', '??')
        self.equations = extras.get('equations', '??')
        self.listing = extras.get('listing', '??')
        self.listings = extras.get('listings', '??')
        self.section = extras.get('section', '??')
        self.sections = extras.get('sections', '??')

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
                'output_decimal_marker': ',',
                'list_final_separator': 'a',
                'list_pair_separator': 'a',
            }
        }


languages = [
    Locale('sk', 'slovak', 'sk-SK', ('„', '“'),
           figure='obrázok', figures='obrázky',
           table='tabuľka', tables='tabuľky',
           equation='rovnica', equations='rovnice'),
    Locale('en', 'english', 'en-US', ('“', '”'),
           figure='figure', figures='figures',
           table='table', tables='tables',
           equation='equation', equations='equations'),
    Locale('cs', 'czech', 'cs-CZ', ('„', '“'),
           figure='obrázek', figures='obrázky',
           table='tabulka', tables='tabulky',
           equation='rovnice', equations='rovnice'),
    Locale('ru', 'russian', 'ru-RU', ('«', '»'),
           figure='фигура', figures='фигуры',
           table='таблица', tables='таблицы',
           equation='уравнение', equations='уравнения'),
    Locale('de', 'german', 'de-DE', ('„', '“'),
           figure='ausbildung', figures='ausbildungen',
           table='tabelle', tables='tabellen',
           equation='gleichung', equations='gleichungen'),
    Locale('pl', 'polish', 'pl-PL', ('„', '“'),
           figure='figura', figures='figury',
           table='tabela', tables='tabely',
           equation='równanie', equations='równania'),
    Locale('hu', 'hungarian', 'hu-HU', ('„', '“'),
           figure='ábra', figures='ábrák',
           table='táblázat', tables='táblázatok',
           equation='egyenlet', equations='egyenletek'),
    Locale('fr', 'french', 'fr-FR', ('«\u202F', '\u202F»'),
           figure='figure', figures='figures',
           table='tableau', tables='tableaux',
           equation='équation', equations='équations',),
    Locale('es', 'spanish', 'es-ES', ('«', '»'),
           figure='figura', figures='figuras',
           table='tabla', tables='tables',
           equation='ecuación', equations='ecuacións'),
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
        Optional('figure'): str,
        Optional('figures'): str,
        Optional('table'): str,
        Optional('tables'): str,
        Optional('equation'): str,
        Optional('equations'): str,
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
