from enschema import Schema, Optional


class Locale:
    def __init__(self, code, name, locale, quotes, *, rtl=False, **extras):
        self.id = code
        self.name = name
        self.locale = locale
        self.quotes = quotes
        self.rtl = rtl
        self.quotes_extra = extras.get('quotes_extra', '')

        for k, v in extras.items():
            self.__setattr__(k, v)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'locale': self.locale,
            'quotes': {
                'open': self.quotes[0],
                'close': self.quotes[1],
                'id': self.name,
                'extra': self.quotes_extra,
            },
            'rtl': self.rtl,
            'figure': self.figure,
            'figures': self.figures,
            'table': self.table,
            'tables': self.tables,
            'equation': self.equation,
            'equations': self.equations,
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
        Optional('rtl', default=False): bool,
    }
})
