"""
The locale schema, which until recently checked nothing it claimed to.

`core/i18n/<lang>.yaml` is validated against `Locale.schema`, and seven of its entries were
written as subscripted generics -- `dict[str, str]`, `list[str]`. enschema reads one of those as a
*callable* and validates by calling it, so `list[str]` only ever asked whether the value could be
passed to `list()`. It always can: `list('aiko')` is `['a', 'i', 'k', 'o']`, so a `singles:`
written as a bare string would have become a list of its letters, and every one of those letters
would then have been glued to the word after it by `spacing.lua`.

The same hole hid a schema that was simply **wrong**: `prefixes` was declared
`dict[str, dict[str, str]]` and is really keyed by the exponent, `3: {name: kilo, symbol: k}`.
Nothing had ever compared the two.

So: every real locale still validates, and the shapes that merely look like the real ones do not.
"""
import copy

import pytest
import yaml
from enschema import SchemaError

from core.i18n import Locale, languages, merge

DEFAULTS = 'core/i18n/default.yaml'


@pytest.fixture(scope='module')
def complete():
    """One real locale, merged with the defaults exactly as `load_yaml` merges it."""
    with open(DEFAULTS) as f, open('core/i18n/sk.yaml') as g:
        return merge(yaml.safe_load(f), yaml.safe_load(g))


@pytest.fixture
def mutate(complete):
    """Build a locale from the real data with one thing changed, and say whether it validates."""
    def call(change):
        data = copy.deepcopy(complete)
        change(data)
        Locale('sk', **data)
    return call


class TestTheRealLocalesStillLoad:
    """The half that matters most: a tightened schema that rejects real data is worse than none."""

    def test_every_shipped_locale_validates(self):
        assert len(languages) >= 12
        for code, locale in languages.items():
            assert locale.full, f'{code} loaded without a name'

    def test_the_fixture_itself_validates(self, mutate):
        mutate(lambda data: None)


class TestTheShapesThatLookRightAndAreNot:
    @pytest.mark.parametrize(('change', 'what'), [
        (lambda d: d['typography'].__setitem__('singles', 'aiko'),
         'singles written as a bare string, which `list()` would silently split into letters'),
        (lambda d: d['typography'].__setitem__('singles', ['a', 5]), 'a number among the singles'),
        (lambda d: d['typography'].__setitem__('nbsp_pairs', 't. j.'), 'nbsp_pairs as a string'),
        (lambda d: d['words'].__setitem__('and', ['a']), 'a word whose text is a list'),
        (lambda d: d['siunitx']['units'].__setitem__('metre', 5), 'a unit symbol that is a number'),
        (lambda d: d['siunitx']['prefixes'].__setitem__(3, {'name': 'kilo'}),
         'a prefix with no symbol'),
        (lambda d: d['siunitx']['prefixes'].__setitem__('kilo', {'name': 'k', 'symbol': 'k'}),
         'a prefix keyed by its name rather than its exponent'),
        (lambda d: d['siunitx']['prefixes'].__setitem__(3, 'kilo'), 'a prefix that is a string'),
    ])
    def test_it_is_rejected(self, mutate, change, what):
        with pytest.raises(SchemaError):
            mutate(change)

    @pytest.mark.parametrize(('change', 'what'), [
        (lambda d: d['typography'].__setitem__('thin_pairs', []), 'an empty list of pairs'),
        (lambda d: d['typography'].pop('singles'), 'a language that declares no singles'),
        (lambda d: d['typography'].__setitem__('repeat_hyphen', True), 'the hyphen flag'),
        (lambda d: d.__setitem__('latex', {'exhyphenpenalty': 50}), 'a LaTeX penalty'),
    ])
    def test_the_quiet_cases_are_left_alone(self, mutate, change, what):
        """
        A language that declares nothing gets nothing, and that is the design -- `default.yaml`
        deliberately carries no `words:` and no `typography:`, so absence has to stay legal.
        """
        mutate(change)
