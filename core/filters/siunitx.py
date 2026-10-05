r"""
siunitx expanded into ordinary TeX, for the formats that have no siunitx to expand it.

The PDF gets real siunitx. The web gets MathJax, which **has no siunitx at all** -- neither the
modern `\qty` nor the older `\SI` is defined there, and no extension supplies them for MathJax 3
or 4. The usual answer is a pile of MathJax macros, and it works right up to the point where
siunitx would have to *look inside* an argument: `\qtylist{1;2;3}{\metre}` is three values, and a
macro can only paste the argument back whole. A macro is a substitution; siunitx is a parser.

So the parsing happens here instead, before pandoc, and the HTML carries only maths any renderer
can read. `\qty{1.0e+15}{\joule}` leaves as `1.0\cdot10^{15}\ \text{J}`.

**Every choice below is read off the document's own settings rather than picked**, because the
page and the booklet have to agree:

- `core/latex/siunitx.tex`'s `\sisetup` gives the separators, `per-mode = symbol` (so `m/s`, not
  `m\,s^{-1}`), `exponent-product = \cdot`, `number-unit-product = {\ }`, and grouping that
  starts at five digits;
- the locale gives the decimal marker and the two list separators -- Slovak writes `83{,}5` and
  `1 m, 2 m a 3 m` -- exactly as `core/templates/override.jtex` emits them for LaTeX;
- the unit symbols come from the locale's own table first, which is what that same template
  re-declares per language, and from `siunitx.tex`'s custom declarations second.

What it deliberately does not do: `group-separator` is applied to the integer part only, and the
`[...]` option list a call may carry is dropped rather than honoured. Both are visible in the TeX
and neither occurs in the sources in a form where it would change the reading.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path

#: `core/latex/siunitx.tex`'s `\sisetup`, which is the booklet's own.
PER = '/'
EXPONENT_PRODUCT = r'\cdot'
NUMBER_UNIT_PRODUCT = r'\ '
GROUP_SEPARATOR = r'\,'
GROUP_MINIMUM_DIGITS = 5
# An en dash outright, not TeX's `--` ligature: `\text{ -- }` is what `\sisetup` writes and
# what LaTeX turns into one, but MathJax has no such ligature and would set two hyphens.
RANGE_PHRASE = '\\text{ \u2013 }'
LIST_SEPARATOR = r'\text{,}\ '
PRODUCT_SEPARATOR = r'\times'

#: Units siunitx defines itself and neither the locale nor `siunitx.tex` re-declares, so nothing
#: in the repository would otherwise say what they print.
BUILTIN = {
    'percent': r'\%', 'kilogram': 'kg', 'mol': 'mol', 'degree': r'^\circ',
    'degreeCelsius': r'^\circ\text{C}', 'arcminute': r'^\prime', 'arcsecond': r'^{\prime\prime}',
    'gram': 'g', 'litre': 'l', 'liter': 'l', 'tonne': 't', 'bel': 'B', 'neper': 'Np',
    'astronomicalunit': 'au', 'electronvolt': 'eV', 'dalton': 'Da', 'bar': 'bar',
}

#: `\per` and the two powers are operators on the unit string, not units.
OPERATORS = {'per': PER, 'squared': '^{2}', 'cubed': '^{3}', 'square': '^{2}', 'cubic': '^{3}'}
#: siunitx's two argument-taking powers. They are what a *computed* unit reaches for when the
#: exponent is not 2 or 3 -- the cube root of a volume in litres is `\litre\tothe{0.333}` -- so
#: they arrive from the quantity formatter rather than from an author, and dropping the argument
#: left `\tothe` on the page as a red undefined macro beside a unit with no power at all.
POWERS = {'tothe', 'raiseto'}

#: How many brace groups each command takes, and how to assemble them.
ARITY = {
    'num': 1, 'unit': 1, 'ang': 1, 'numlist': 1, 'numproduct': 1, 'si': 1,
    'qty': 2, 'qtylist': 2, 'qtyproduct': 2, 'numrange': 2, 'SI': 2, 'SIlist': 2,
    'qtyrange': 3, 'SIrange': 3,
}

_DECLARED = re.compile(r'\\DeclareSIUnit(?:\[[^\]]*\])?\{\\(\w+)\}\{(.*)\}')
_MACRO = re.compile(r'\\([a-zA-Z]+)(?:\{([^{}]*)\})?')
_COMMAND = re.compile(r'\\(' + '|'.join(sorted(ARITY, key=len, reverse=True)) + r')(?![a-zA-Z])')


@functools.cache
def declared_units(path: str = 'core/latex/siunitx.tex') -> dict[str, str]:
    """
    The repository's own `\\DeclareSIUnit`s, read rather than copied.

    Parsed from the file the booklet loads, so a unit added there reaches the web without anybody
    remembering a second table.
    """
    source = Path(path)
    if not source.is_file():
        return {}
    return {m.group(1): m.group(2) for m in _DECLARED.finditer(source.read_text())}


def _merge(text: str) -> str:
    r"""`\text{k}\text{g}` is `\text{kg}`. Only tidier, but this is the commonest output there is."""
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r'\\text\{([^{}]*)\}\\text\{([^{}]*)\}', r'\\text{\1\2}', text)
    return text


def _mathsafe(tex: str) -> str:
    r"""
    A declared symbol made safe for maths: every bare letter run wrapped in `\text{}`.

    `siunitx.tex` writes degrees Celsius as `\text{°}C`, which is right in a `\unit{}` and wrong
    anywhere else -- the `C` sits in maths and comes out italic, as a variable would. Letters
    already inside a group are left alone, so `\textit{g}` and `\ensuremath{\mathrm{M}_{\Sun}}`
    pass through untouched.
    """
    if not any(c in tex for c in '\\{^'):
        return rf'\text{{{tex}}}'
    out, i, depth = [], 0, 0
    while i < len(tex):
        if (command := re.match(r'\\[a-zA-Z]+|\\.', tex[i:])) is not None:
            out.append(command.group(0))
            i += command.end()
        elif tex[i] in '{}':
            depth += 1 if tex[i] == '{' else -1
            out.append(tex[i])
            i += 1
        elif depth == 0 and (letters := re.match(r'[A-Za-z]+', tex[i:])) is not None:
            out.append(rf'\text{{{letters.group(0)}}}')
            i += letters.end()
        else:
            out.append(tex[i])
            i += 1
    return ''.join(out)


def symbol(name: str, locale) -> str:
    """
    What one unit macro prints, in this language.

    The locale's own table first -- `override.jtex` re-declares those per language, so Slovak may
    spell a unit differently from English and the page must follow the booklet. Then the
    repository's custom declarations, then siunitx's own.
    """
    units = (locale.data.get('siunitx') or {}).get('units') or {} if locale else {}
    if name in units:
        return rf'\text{{{units[name]}}}'
    prefixes = (locale.data.get('siunitx') or {}).get('prefixes') or {} if locale else {}
    for entry in prefixes.values():
        if entry.get('name') == name:
            return rf'\text{{{entry["symbol"]}}}'
    if name in declared_units():
        return _mathsafe(declared_units()[name])
    if name in BUILTIN:
        return _mathsafe(BUILTIN[name])
    # Not a unit we know. Leave the macro standing so it is visible rather than silently dropped.
    return f'\\{name}'


def format_number(text: str, locale) -> str:
    r"""
    A number as siunitx would set it: the locale's decimal marker, grouping, and an exponent.

    `1.0e+15` becomes `1.0\cdot10^{15}`; an empty mantissa -- which `cut_extra_one` produces so
    that siunitx sets a bare power of ten -- becomes `10^{15}` with no stray product sign.
    """
    marker = ((locale.data.get('siunitx') or {}).get('output_decimal_marker')
              if locale else None) or '.'
    text = text.strip()

    def plain(value: str) -> str:
        value = value.strip()
        # `value[:1] in '+-'` is **true for the empty string**, because every string contains the
        # empty one -- so a `\num{}` used to reach `value[0]` and take the whole HTML build down
        # with an `IndexError` naming nothing. An empty argument is not a number; it is left as
        # the empty string, the way an unparseable one is left standing.
        sign, digits = (value[0], value[1:]) if value[:1] in ('+', '-') else ('', value)
        whole, point, fraction = digits.partition('.')
        # Only a run of digits is grouped. An argument may be an expression -- `\num{\frac12}` --
        # and inserting thin spaces into markup would corrupt it.
        if whole.isdigit() and len(whole) >= GROUP_MINIMUM_DIGITS:
            groups = []
            while len(whole) > 3:
                groups.insert(0, whole[-3:])
                whole = whole[:-3]
            whole = GROUP_SEPARATOR.join([whole, *groups])
        if not point:
            return sign + whole
        # A comma is punctuation in maths and would take punctuation spacing, so it is wrapped.
        # A full stop needs nothing and is left bare, which keeps the common case unremarkable.
        shown = marker if marker == '.' else f'{{{marker}}}'
        return f'{sign}{whole}{shown}{fraction}'

    scientific = re.match(r'^(.*?)[eE]([-+]?\d+)$', text)
    if not scientific:
        return plain(text)
    mantissa, exponent = scientific.group(1), int(scientific.group(2))
    power = rf'10^{{{exponent}}}'
    return power if not mantissa.strip() else f'{plain(mantissa)}{EXPONENT_PRODUCT}{power}'


def format_unit(text: str, locale) -> str:
    r"""
    A unit macro chain as one TeX string: `\kilo\gram\per\metre\cubed` becomes `\text{kg}/\text{m}^{3}`.

    `inter-unit-product` is empty in the booklet's `\sisetup`, so symbols simply abut and a prefix
    needs no special handling -- `\kilo` then `\gram` is `k` then `g`. `per-mode` is `symbol`, so
    `\per` is a solidus and applies to what follows it, which is what makes `J/kg/K` read the way
    the booklet sets it.
    """
    out = []
    for name, argument in _MACRO.findall(text):
        if name in POWERS:
            out.append(f'^{{{argument}}}')
        elif name in OPERATORS:
            out.append(OPERATORS[name])
        else:
            out.append(symbol(name, locale))
    return _merge(''.join(out))


def _group(text: str, start: int) -> tuple[str, int]:
    """One brace group beginning at `start`, and where it ends. Nesting-aware."""
    assert text[start] == '{'
    depth, i = 0, start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError(f'unbalanced braces from {start}')


def _arguments(text: str, start: int, count: int) -> tuple[list[str], int] | None:
    """`count` brace groups from `start`, stepping over an option list and any whitespace."""
    i = start
    if i < len(text) and text[i] == '[':          # `\qty[per-mode=symbol]{…}{…}`
        close = text.find(']', i)
        if close < 0:
            return None
        i = close + 1
    found = []
    for _ in range(count):
        while i < len(text) and text[i] in ' \t\n':
            i += 1
        if i >= len(text) or text[i] != '{':
            return None
        try:
            argument, i = _group(text, i)
        except ValueError:
            return None                 # unbalanced: leave the call exactly as it was
        found.append(argument)
    return found, i


def _assemble(command: str, arguments: list[str], locale) -> str:
    """One siunitx call as plain TeX."""
    separators = (locale.data.get('siunitx') or {}) if locale else {}
    final = separators.get('list_final_separator') or 'and'
    pair = separators.get('list_pair_separator') or 'and'
    number = functools.partial(format_number, locale=locale)
    unit = functools.partial(format_unit, locale=locale)

    def joined(values: list[str], render) -> str:
        """A list, with the locale's word before the last item -- `1 m, 2 m a 3 m`."""
        shown = [render(v) for v in values]
        if len(shown) == 1:
            return shown[0]
        word = rf'\text{{ {pair if len(shown) == 2 else final} }}'
        return (LIST_SEPARATOR.join(shown[:-1]) if len(shown) > 2 else shown[0]) + word + shown[-1]

    match command:
        case 'num':
            return number(arguments[0])
        case 'unit' | 'si':
            return unit(arguments[0])
        case 'qty' | 'SI':
            return f'{number(arguments[0])}{NUMBER_UNIT_PRODUCT}{unit(arguments[1])}'
        case 'ang':
            # `\ang{44;9;}` is degrees, arcminutes, arcseconds -- siunitx splits it, so this does.
            parts = arguments[0].split(';')
            if len(parts) == 1:
                return rf'{number(parts[0])}^\circ'
            marks = [r'^\circ', r'^\prime', r"^{\prime\prime}"]
            return r'\,'.join(f'{number(p)}{m}' for p, m in zip(parts, marks) if p.strip())
        case 'numrange':
            return f'{number(arguments[0])}{RANGE_PHRASE}{number(arguments[1])}'
        case 'qtyrange' | 'SIrange':
            # `range-units = repeat`, so the unit is set on both ends.
            tail = f'{NUMBER_UNIT_PRODUCT}{unit(arguments[2])}'
            return f'{number(arguments[0])}{tail}{RANGE_PHRASE}{number(arguments[1])}{tail}'
        case 'numlist':
            return joined(arguments[0].split(';'), number)
        case 'qtylist' | 'SIlist':
            tail = f'{NUMBER_UNIT_PRODUCT}{unit(arguments[1])}'      # `list-units = repeat`
            return joined(arguments[0].split(';'), lambda v: number(v) + tail)
        case 'numproduct':
            return PRODUCT_SEPARATOR.join(number(v) for v in arguments[0].split(' x '))
        case 'qtyproduct':
            tail = f'{NUMBER_UNIT_PRODUCT}{unit(arguments[1])}'
            return PRODUCT_SEPARATOR.join(number(v) + tail for v in arguments[0].split(' x '))
    raise ValueError(f'unknown siunitx command {command!r}')


def expand(text: str, locale=None) -> str:
    """
    Every siunitx call in `text`, rewritten as plain TeX. Anything else is returned untouched.

    A call whose arguments do not parse is left exactly as it was: better a visible `\\qty` on the
    page than a silently mangled number.
    """
    out, i = [], 0
    while (found := _COMMAND.search(text, i)) is not None:
        parsed = _arguments(text, found.end(), ARITY[found.group(1)])
        if parsed is None:
            out.append(text[i:found.end()])
            i = found.end()
            continue
        arguments, end = parsed
        out.append(text[i:found.start()])
        out.append(_merge(_assemble(found.group(1), arguments, locale)))
        i = end
    out.append(text[i:])
    return ''.join(out)
