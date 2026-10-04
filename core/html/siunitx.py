r"""
siunitx for the web, because MathJax has no extension for it and the sources make ~9200 calls.

This is the source of truth for the Lua filter that does the rewriting: it holds the unit
vocabulary and the `\sisetup` settings, and writes them out as `core/filters/siunitx-table.lua`.
`python -m core.html.siunitx` regenerates that file and `--check` exits nonzero when it is stale,
which is the CI shape `core/audit/macros.py` and `core/builder/reference.py` already use.

**The custom units are parsed out of `core/latex/siunitx.tex` rather than transcribed.** Forty of
them are declared there, and a `\DeclareSIUnit` added tomorrow has to reach the web without anyone
remembering this file -- which is the same argument `docs/filters.md` makes about the filter table.

The rest is transcribed, and the list is not a guess: it is every unit macro the corpus actually
writes inside a `\qty`, `\unit`, `\SI` or `\si`, collected by a sweep. That includes a handful of
spellings this repository's own conventions disallow -- `\meter`, `\kilogram`, `\cubic\metre` --
which are in `ALIASES` rather than `UNITS`, so they render correctly and stay reportable.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

#: Where the custom units are declared, and where the `\sisetup` this must reproduce lives.
SIUNITX_TEX = pathlib.Path('core/latex/siunitx.tex')
#: What this module writes.
TABLE_LUA = pathlib.Path('core/filters/siunitx-table.lua')

#: SI prefixes. The symbol is what goes on the page, directly in front of the unit.
PREFIXES = {
    'yocto': 'y', 'zepto': 'z', 'atto': 'a', 'femto': 'f', 'pico': 'p', 'nano': 'n',
    'micro': r'\mu', 'milli': 'm', 'centi': 'c', 'deci': 'd',
    'deca': 'da', 'hecto': 'h', 'kilo': 'k', 'mega': 'M', 'giga': 'G', 'tera': 'T',
    'peta': 'P', 'exa': 'E', 'zetta': 'Z', 'yotta': 'Y',
}

#: The units siunitx itself defines, restricted to the ones the corpus writes. Keeping it to
#: those is deliberate: a unit nobody uses cannot be checked against a rendered page, and an
#: unchecked entry in a table like this is how a wrong symbol survives.
UNITS = {
    # base
    'metre': 'm', 'gram': 'g', 'second': 's', 'ampere': 'A', 'kelvin': 'K',
    'mole': 'mol', 'candela': 'cd',
    # derived
    'hertz': 'Hz', 'newton': 'N', 'pascal': 'Pa', 'joule': 'J', 'watt': 'W',
    'coulomb': 'C', 'volt': 'V', 'farad': 'F', 'ohm': r'\Omega', 'siemens': 'S',
    'weber': 'Wb', 'tesla': 'T', 'henry': 'H', 'lumen': 'lm', 'lux': 'lx',
    'becquerel': 'Bq', 'gray': 'Gy', 'sievert': 'Sv', 'katal': 'kat',
    # accepted for use with SI
    'degreeCelsius': r'^\circ\mathrm{C}', 'radian': 'rad', 'steradian': 'sr',
    'minute': 'min', 'hour': 'h', 'day': 'd', 'degree': r'^\circ',
    'arcminute': "'", 'arcsecond': "''", 'tonne': 't', 'electronvolt': 'eV',
    'percent': r'\%', 'bel': 'B', 'decibel': 'dB', 'neper': 'Np',
    'astronomicalunit': 'au', 'knot': 'kn',
}

#: Spellings that mean a unit already in the tables. Some are siunitx's own synonyms; some this
#: repository tells authors not to write (`\meter`, `\kilogram`, `\cubic\metre`), and those stay
#: here rather than in `UNITS` so that rendering them correctly does not bless them.
ALIASES = {
    'meter': ['metre'], 'liter': ['litre'], 'kilogram': ['kilo', 'gram'],
    'kg': ['kilo', 'gram'], 'm': ['metre'], 'mol': ['mole'], 'atm': ['atmosphere'],
    'celsius': ['degreeCelsius'], 'lightspeed': ['metre', 'per', 'second'],
}

#: Powers, and the one that reads backwards: `\per` applies to the unit *after* it.
POWERS = {'squared': 2, 'cubed': 3, 'tothe': None, 'raiseto': None}
#: `\cubic\metre` is `\metre\cubed` written the other way round -- a spelling the conventions
#: disallow and the corpus still contains.
PREFIX_POWERS = {'square': 2, 'cubic': 3}

#: `\sisetup` from `core/latex/siunitx.tex`, which the web has to reproduce because nothing else
#: will. Transcribed with the key names as siunitx spells them, so the two can be read together.
SETTINGS = {
    # `m/s`, not `m s^{-1}`
    'per-mode': 'symbol',
    # a thin space every three digits, but only from five digits up: `1000` and `10\,000`
    'group-separator': r'\,',
    'group-minimum-digits': 5,
    # nothing at all between two units
    'inter-unit-product': '',
    # `5.1 \cdot 10^{7}`, not `5.1 \times 10^{7}`
    'exponent-product': r'\cdot',
    # a non-breaking thin space between the number and its unit
    'number-unit-product': r'\,',
    # both ends of a range carry the unit, and this is what stands between them. `\text{}`,
    # and a literal en dash: the LaTeX writes `\text{ -- }` and relies on the font's `tex-text`
    # mapping to turn `--` into one, which MathJax does not do.
    'range-phrase': r'\text{ – }',
    'range-units': 'repeat',
    'list-separator': r'\text{, }',
    'list-units': 'repeat',
    'product-units': 'repeat',
}

RE_DECLARE = re.compile(r'^\\DeclareSIUnit(?:\[[^]]*\])?\{\\(?P<name>[A-Za-z]+)\}\{(?P<symbol>.*)\}$',
                        re.MULTILINE)


def custom_units(path: pathlib.Path = SIUNITX_TEX) -> dict[str, str]:
    r"""
    The `\DeclareSIUnit` units, read out of the LaTeX rather than copied into Python.

    Forty of them, and the point of reading them is that the forty-first arrives here by itself.
    """
    return {m['name']: m['symbol'] for m in RE_DECLARE.finditer(path.read_text())}


def lua_literal(value) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def lua_table(name: str, mapping: dict, *, comment: str = '') -> str:
    out = [f'-- {comment}'] if comment else []
    out.append(f'M.{name} = {{')
    for key, value in mapping.items():
        if isinstance(value, list):
            rendered = '{' + ', '.join(lua_literal(v) for v in value) + '}'
        else:
            rendered = lua_literal(value)
        out.append(f'    ["{key}"] = {rendered},')
    out.append('}')
    return '\n'.join(out)


def generate() -> str:
    """The Lua table, as text. Everything here is data; the parsing lives in `siunitx.lua`."""
    units = dict(UNITS)
    units.update(custom_units())
    return '\n\n'.join([
        ('-- GENERATED by `python -m core.html.siunitx`. Do not edit.\n'
         '--\n'
         '-- The unit vocabulary and the `\\sisetup` settings that `siunitx.lua` rewrites with.\n'
         '-- The custom units come from `core/latex/siunitx.tex`, so the two cannot disagree.\n'
         'local M = {}'),
        lua_table('prefixes', PREFIXES, comment='SI prefixes'),
        lua_table('units', units, comment='siunitx units plus every \\DeclareSIUnit in siunitx.tex'),
        lua_table('aliases', ALIASES, comment='spellings that mean a unit above'),
        lua_table('powers', {k: (v if v is not None else 0) for k, v in POWERS.items()},
                  comment='0 means the power is an argument'),
        lua_table('prefix_powers', PREFIX_POWERS, comment='`\\cubic\\metre`, the other way round'),
        lua_table('settings', SETTINGS, comment='\\sisetup from core/latex/siunitx.tex'),
        'return M\n',
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--check', action='store_true',
                        help="do not write; exit nonzero if the file on disk is stale")
    args = parser.parse_args()

    table = generate()
    if args.check:
        current = TABLE_LUA.read_text() if TABLE_LUA.is_file() else None
        if current == table:
            print(f'{TABLE_LUA} is up to date')
            return 0
        print(f'{TABLE_LUA} is stale: run `python -m core.html.siunitx`', file=sys.stderr)
        return 1
    TABLE_LUA.parent.mkdir(parents=True, exist_ok=True)
    TABLE_LUA.write_text(table)
    print(f'wrote {TABLE_LUA}: {len(UNITS)} units + {len(custom_units())} declared, '
          f'{len(PREFIXES)} prefixes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
