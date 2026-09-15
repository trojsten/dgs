r"""
`\unit{…}` -> siunitx.

The old `\unit` is `mathab.sty`'s, and it is not today's. It takes a **literal string** and sets
it upright — `\unit{km/h}`, `\unit{^\circ C}`, `\unit{kJ\,kg^{-1}}` — with the quantity written
outside it, as `$120\unit{km/h}$`. Modern siunitx's `\unit{}` takes unit *macros* and its `\qty{}`
takes the number too, so every one of these has to be read and re-spelled.

The table is deliberately literal rather than clever. A parser for `kJ\,kg^{-1}` would be a small
dimensional-analysis engine, and it would be wrong in exactly the cases that matter — `rad\,s`
appears once in 2009 and is either radian-seconds or a typo for rad/s, which no parser can settle.
Anything not in the table is left alone and reported.
"""
import re

#: `\unit{…}` body -> siunitx unit macros. Keys are the exact source text with whitespace
#: collapsed. Built from what 2009 actually uses; other years extend it.
UNITS = {
    # length
    'm': r'\metre', 'cm': r'\centi\metre', 'mm': r'\milli\metre', 'km': r'\kilo\metre',
    'm^2': r'\metre\squared', 'km^2': r'\kilo\metre\squared', 'm^3': r'\metre\cubed',
    # mass
    'kg': r'\kilo\gram', 'g': r'\gram', 't': r'\tonne',
    # time
    's': r'\second', 'min': r'\minute', 'h': r'\hour',
    # speed and acceleration
    'm/s': r'\metre\per\second', r'm\,s^{-1}': r'\metre\per\second',
    'km/h': r'\kilo\metre\per\hour', r'km\,h^{-1}': r'\kilo\metre\per\hour',
    # The 2007 dialect spells a compound unit with a `.` between the parts, and 2012 still
    # carries a few: `\textrm{km.h}^{-1}`, `\textrm{m.s}^{-1}`.
    'km.h^{-1}': r'\kilo\metre\per\hour', 'm.s^{-1}': r'\metre\per\second',
    'm.s^{-2}': r'\metre\per\second\squared',
    'g.cm^{-3}': r'\gram\per\centi\metre\cubed',
    'kg.m^{-3}': r'\kilo\gram\per\metre\cubed',
    r'm\,s^{-2}': r'\metre\per\second\squared', 'm/s^2': r'\metre\per\second\squared',
    r'km\,h^{-2}': r'\kilo\metre\per\hour\squared',
    # temperature
    'K': r'\kelvin', r'^\circ C': r'\celsius', '^{\\circ}C': r'\celsius',
    # angle
    'rad': r'\radian',
    # force, pressure, energy, power
    'N': r'\newton', 'Pa': r'\pascal', 'J': r'\joule', 'kJ': r'\kilo\joule',
    'mJ': r'\milli\joule', 'W': r'\watt', 'kW': r'\kilo\watt',
    r'kJ\,kg^{-1}': r'\kilo\joule\per\kilo\gram', 'kJ/kg': r'\kilo\joule\per\kilo\gram',
    r'W\,m^{-1}\,K^{-1}': r'\watt\per\metre\per\kelvin',
    # electricity
    'V': r'\volt', 'kV': r'\volt', 'A': r'\ampere', 'F': r'\farad',
    r'\Omega': r'\ohm', r'k\Omega': r'\kilo\ohm', r'M\Omega': r'\mega\ohm',
    r'kV\,mm^{-1}': r'\kilo\volt\per\milli\metre',
    r'kJ\,kg^{-1}\,K^{-1}': r'\kilo\joule\per\kilo\gram\per\kelvin',
    r'W\,\Ce^{-1}': r'\watt\per\celsius',
    'cm^2': r'\centi\metre\squared',
    r'F\,m^{-1}': r'\farad\per\metre',
    r'g\,mol^{-1}': r'\gram\per\mole',
    # other
    'Hz': r'\hertz', 'dB': r'\decibel', 'l': r'\litre', 'L': r'\litre',
    r'\%': r'\percent', r'^\circ': r'\degree', '^{\\circ}': r'\degree',
    'kms^{-1}': r'\kilo\metre\per\second', r'km\,s^{-1}': r'\kilo\metre\per\second',
    'J.kg^{-1}K^{-1}': r'\joule\per\kilo\gram\per\kelvin',
    r'J\,kg^{-1}\,K^{-1}': r'\joule\per\kilo\gram\per\kelvin',
    'J/kg': r'\joule\per\kilo\gram',
    'nm': r'\nano\metre', 'kPa': r'\kilo\pascal', 'MPa': r'\mega\pascal',
    r'g\,cm^{-3}': r'\gram\per\centi\metre\cubed',
    r'kg/m^3': r'\kilo\gram\per\metre\cubed',
    r'kg\,m^{-3}': r'\kilo\gram\per\metre\cubed',
}

#: Deliberately absent, so they are reported rather than guessed:
#:
#: `rad\,s`  -- radian-seconds, or a typo for rad/s? It appears once, in 2009, and the statement
#:              does not settle it. A table entry would be a guess wearing a table's authority.

#: `kV` above would drop the prefix; spell the ones with a prefix out separately so it cannot.
UNITS['kV'] = r'\kilo\volt'

#: Zero-argument macros that stand for a whole unit. Their meaning is taken from the **year's**
#: `include.tex` where it defines them, because `mathab.sty` and `include.tex` disagree about
#: `\kmh` and `\ms` and the later definition wins.
MACRO_UNITS = {
    r'\Ce': r'\celsius',
    r'\sdeg': r'\degree',
    r'\kmh': r'\kilo\metre\per\hour',
    r'\ms': r'\metre\per\second',
}


#: `^{3}` and `^3` are the same exponent. The archive spells them both, sometimes in one file,
#: and a table holding only one of them misses the other silently -- 2010 writes `kg/m^{3}` where
#: 2009 wrote `kg/m^3`.
RE_BRACED_EXPONENT = re.compile(r'\^\{(-?\d+)\}')


def _normal(body: str) -> str:
    """One spelling of a unit body: no spaces, and exponents unbraced."""
    return RE_BRACED_EXPONENT.sub(r'^\1', ''.join(body.split()))


def lookup(body: str) -> str | None:
    """siunitx for a `\\unit{…}` body, or None if it is not in the table."""
    key = ' '.join(body.split())
    if key in UNITS:
        return UNITS[key]
    stripped = _normal(key)
    for k, v in UNITS.items():
        if _normal(k) == stripped:
            return v
    return MACRO_UNITS.get(stripped)
