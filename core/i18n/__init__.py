from enschema import Schema, Optional


class Locale:
    def __init__(self, code, name, locale, quotes, *, rtl=False, **extras):
        self.id = code
        self.name = name
        self.locale = locale
        self.quotes = quotes
        self.rtl = rtl

        for k, v in extras.items():
            self.__setattr__(k, v)



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
    Locale('ru', 'russian', 'ru-RU', ('«', '»'), figure=''),
    Locale('de', 'german', 'de-DE', ('„', '“'),
           figure='ausbildung', figures='ausbildungen',
           table='tabelle', tables='tabellen',
           equation='gleichung', equations='gleichungen'),
    Locale('pl', 'polish', 'pl-PL', ('„', '“'),
           figure='figura', figures='figury',
           table='tabela', tables='tabely',
           equation='równanie', equations='równania'),
    Locale('hu', 'hungarian', 'hu-HU', ('„', '“'),
           figure='ábra',
           table='táblázat',
           equation='Egyenlet'),
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
