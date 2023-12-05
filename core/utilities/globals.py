from enschema import Schema, Optional


languages = {
    'sk': {'name': 'slovak'},
    'en': {'name': 'english'},
    'cs': {'name': 'czech'},
    'de': {'name': 'german'},
    'fr': {'name': 'french'},
    'pl': {'name': 'polish'},
    'hu': {'name': 'hungarian'},
    'ru': {'name': 'russian'},
    'fa': {'name': 'persian', 'rtl': True},
    'es': {'name': 'spanish'},
}

LanguageSchema = Schema({
    'language': {
        'id': str,
        'name': str,
        Optional('rtl', default=False): bool,
    }
})
