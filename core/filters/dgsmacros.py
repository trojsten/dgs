r"""
This repository's own macros expanded into ordinary TeX, for the formats that have no LaTeX.

The booklet gets `core/latex/math.tex`. The web gets MathJax, which has none of it -- and a
MathJax macro cannot be given the families that matter, for the same reason `core/filters/
siunitx.py` exists. A MathJax macro is a fixed-arity substitution: `macros: {Paren: ['\\left(#1
\\right)', 1]}` works, and nothing of that shape can express

    \Int[0][T]{v(t)}{t}          two optional arguments, then two mandatory ones
    \Expected{X}[n]              an optional argument *after* a mandatory one
    \FDiff^{2}_{\text{vap}}{H}   an embellishment that takes `^` and `_` in either order
    \Coord{-d; d}                one argument that has to be split on `;`

`\Diff` and `\FDiff` alone are written 1 788 times in `source/`. Left to MathJax they are red
undefined-macro boxes, which is what the whole custom vocabulary looked like on the page.

So the parsing happens here, before pandoc, exactly as it does for siunitx, and the fragment
carries only maths any renderer can read. The fixed-arity half of the vocabulary stays in
`tools/editor/static/mathjax-dgs.js`, where a macro is the right tool and costs nothing.

**The expansions are read off `core/latex/math.tex`**, not invented, so the page and the booklet
agree; where that file has a known defect the expansion reproduces the *fixed* behaviour, since
the two were repaired together.

A call whose arguments do not parse is left exactly as it was. A visible `\Int` on the page is a
better failure than a silently mangled integral.
"""
from __future__ import annotations

import re

#: What `math.tex` calls the four differentials.
DIFFERENTIAL = {'Diff': r'\mathrm{d}', 'PDiff': r'\partial',
                'FDiff': r'\Delta', 'UDiff': r'\delta'}

#: The fraction styles `\SetDerivativeFrac@` chooses between.
FRACTION = {'d': r'\dfrac', 't': r'\tfrac', 's': r'\frac', 'n': r'\frac', '': r'\frac'}


class Arguments:
    r"""
    One call's arguments, read in `math.tex`'s own xparse spelling.

    `O` is an optional `[...]` defaulting to empty, `o` the same defaulting to None, `m` a
    mandatory `{...}`, and `A` the angle-bracketed `<...>` that selects a fraction style. The
    signature is the macro's own, copied from its `\NewDocumentCommand`.
    """
    def __init__(self, text: str, start: int):
        self.text, self.i = text, start

    def _skip(self) -> None:
        while self.i < len(self.text) and self.text[self.i] in ' \t':
            self.i += 1

    def _balanced(self, opening: str, closing: str) -> str | None:
        self._skip()
        if self.i >= len(self.text) or self.text[self.i] != opening:
            return None
        depth, j = 0, self.i
        while j < len(self.text):
            if self.text[j] == '\\':
                j += 2
                continue
            if self.text[j] == opening:
                depth += 1
            elif self.text[j] == closing:
                depth -= 1
                if depth == 0:
                    body = self.text[self.i + 1:j]
                    self.i = j + 1
                    return body
            j += 1
        return None

    #: A mandatory argument given as a bare token: one control word, or one character.
    TOKEN = re.compile(r'\\[A-Za-z]+|[^\s\\{}\[\]]')

    def _token(self) -> str | None:
        r"""
        A mandatory argument written without braces.

        xparse takes a single token for `m`, so `\Diff I` and `\Diff t` are legal and are
        written -- `07/integrals` has `\frac{\Diff I}{I}`. Requiring the braces left those as
        red undefined-macro boxes on the page while the booklet set them correctly, which is
        exactly the kind of web-only divergence this filter exists to close.

        A single *letter* counts only when a letter does not follow it. TeX would take the `f`
        out of `\Int family` and be right to; this runs over the whole line, prose included, and
        a macro named in a sentence is far commoner than `\Diff tx`. Refusing costs nothing --
        the call is left as it was, which is visible -- while taking it would eat two words.
        """
        self._skip()
        found = self.TOKEN.match(self.text, self.i)
        if found is None:
            return None
        if not found.group().startswith('\\') and found.end() < len(self.text) \
                and self.text[found.end()].isalpha():
            return None
        self.i = found.end()
        return found.group()

    def read(self, signature: str) -> list | None:
        out = []
        for kind in signature:
            if kind in 'Oo':
                value = self._balanced('[', ']')
                out.append('' if (value is None and kind == 'O') else value)
            elif kind == 'A':
                value = self._balanced('<', '>')
                out.append(value or '')
            elif kind == 'm':
                value = self._balanced('{', '}')
                if value is None:
                    value = self._token()
                if value is None:
                    return None
                out.append(value)
            else:
                raise ValueError(f'unknown argument kind {kind!r}')
        return out


def _cs(command: str) -> str:
    r"""
    A control word and whatever follows it, kept apart.

    `\partial` followed by `u` is the undefined `\partialu`, and `\int` followed by `f` is
    `\intf`. TeX's own parser would have ended the control word at the brace `math.tex` always
    has there; here the braces are gone, so the space has to be put back.
    """
    return command + (' ' if command[-1].isalpha() else '')


def _limits(lower: str, upper: str) -> str:
    """`\\limits_{a}^{b}`, with an absent bound left off rather than printed as an empty one."""
    return (rf'\limits_{{{lower}}}' if lower else '') + (rf'^{{{upper}}}' if upper else '')


def _vec(what: str) -> str:
    return rf'\vec{{{what}}}'


def _paren(what: str) -> str:
    return rf'\left({what}\right)'


#: `\oiint` and `\oiiint` are `esint`'s and MathJax has neither, so the characters stand in.
#: `\mathop` on the two stand-ins because `\limits` is legal only on an operator, and a bare
#: `\unicode{…}` is an ordinary symbol -- MathJax says so outright, in yellow, on the page.
SYMBOL = {'int': r'\int', 'oint': r'\oint', 'iint': r'\iint', 'iiint': r'\iiint',
          'oiint': r'\mathop{\unicode{x222F}}', 'oiiint': r'\mathop{\unicode{x2230}}'}



def _integral(symbol, *, operator='', vector=False, parens=False,
              power='', empty=False, indexed=False):
    r"""
    One member of the integral family.

    `operator` is the `\cdot` or `\times` the `D` and `C` suffixes insert, `vector` the `\vec`
    the `V` suffixes put round both arguments, and `indexed` the `I` suffix's optional power,
    which sits *between* the integrand and the variable rather than before either.
    """
    def build(args):
        lower, upper, *rest = args
        exponent = power
        if indexed:
            integrand, order, variable = rest
            rest, exponent = [integrand, variable], (rf'^{{{order}}}' if order else '')
        if empty:
            variables, integrand = rest, ''
        else:
            integrand, *variables = rest
        if parens:
            integrand = _paren(integrand)
        if vector and integrand:
            integrand = _vec(integrand)
        tail = ''.join(rf'\mathop{{}}\!\mathrm{{d}}{exponent} {_vec(v) if vector else v}'
                       for v in variables if v is not None)
        return f'{_cs(SYMBOL[symbol])}{_limits(lower, upper)}{integrand}{operator}{tail}'
    return build


def _aggregate(operator: str, *, parens=False):
    def build(args):
        lower, upper, body = args
        return rf'{operator}{_limits(lower, upper)}{{{_paren(body) if parens else body}}}'
    return build


def _derivative(kind: str, *, empty=False, parens=False, evaluate=False):
    r"""
    `\Derivative<style>[order]{f}{x}` and its relatives.

    The order goes on **both** halves of the fraction. `math.tex` put it on the numerator alone
    until that was repaired, so a second derivative set `d^2 f / d x`; the expansion follows the
    repaired macro, because the booklet and the page have to agree.
    """
    def build(args):
        if evaluate:
            order, function, variable, at = args
            frac = FRACTION['']
            power = rf'^{{{order}}}' if order else ''
            d = _cs(DIFFERENTIAL[kind])
            return (rf'\left.{frac}{{{d}{power}{function}}}'
                    rf'{{{d}{variable}{power}}}\right|_{{{at}}}')
        style, order, *rest = args
        frac = FRACTION.get(style, FRACTION[''])
        power = rf'^{{{order}}}' if order else ''
        if empty:
            variable, = rest
            return rf'{frac}{{{DIFFERENTIAL[kind]}{power}}}{{{_cs(DIFFERENTIAL[kind])}{variable}{power}}}'
        function, variable = rest
        denominator = ''.join(rf'{_cs(DIFFERENTIAL[kind])}{v.strip()}'
                              for v in variable.split(',')) + power
        if parens:
            return rf'{frac}{{{DIFFERENTIAL[kind]}{power}}}{{{denominator}}}{_paren(function)}'
        return rf'{frac}{{{_cs(DIFFERENTIAL[kind])}{power}{function}}}{{{denominator}}}'
    return build


def _split(opening: str, closing: str, default: str):
    """`\\Coord` and `\\Tuple`: one argument split on `;`, rejoined with the chosen separator."""
    def build(args):
        separator, body = args
        pieces = [p.strip() for p in body.split(';')]
        return rf'\left{opening}{(separator or default).join(pieces)}\right{closing}'
    return build


#: name -> (argument signature, builder). The signatures are `math.tex`'s own.
MACROS = {
    # -- integrals -----------------------------------------------------------------------
    'Int':     ('OOmm',  _integral('int')),
    'IntP':    ('OOmm',  _integral('int', parens=True)),
    'IntX':    ('OOm',   _integral('int')),
    'IntE':    ('OOm',   _integral('int', empty=True)),
    'IntD':    ('OOmm',  _integral('int', operator=r' \cdot ')),
    'IntDV':   ('OOmm',  _integral('int', operator=r' \cdot ', vector=True)),
    'IntC':    ('OOmm',  _integral('int', operator=r' \times ')),
    'IntCV':   ('OOmm',  _integral('int', operator=r' \times ', vector=True)),
    'OInt':    ('Omm',   lambda a: _integral('oint')([a[0], '', a[1], a[2]])),
    'OIntD':   ('Omm',   lambda a: _integral('oint', operator=r' \cdot ')([a[0], '', a[1], a[2]])),
    'OIntDV':  ('Omm',   lambda a: _integral('oint', operator=r' \cdot ', vector=True)([a[0], '', a[1], a[2]])),
    'OIntC':   ('Omm',   lambda a: _integral('oint', operator=r' \times ')([a[0], '', a[1], a[2]])),
    'OIntCV':  ('Omm',   lambda a: _integral('oint', operator=r' \times ', vector=True)([a[0], '', a[1], a[2]])),
    'IInt':    ('OOmmm', _integral('iint')),
    'IIntP':   ('OOmmm', _integral('iint', parens=True)),
    'IIntD':   ('OOmm',  _integral('iint', operator=r' \cdot ')),
    'IIntDV':  ('OOmm',  _integral('iint', operator=r' \cdot ', vector=True)),
    'IIntC':   ('OOmm',  _integral('iint', operator=r' \times ')),
    'IIntCV':  ('OOmm',  _integral('iint', operator=r' \times ', vector=True)),
    'IIntI':   ('OOmOm', _integral('iint', indexed=True)),
    'IIIntI':  ('OOmOm', _integral('iiint', indexed=True)),
    'OIIntI':  ('OOmm',  _integral('oiint')),
    'OIIntC':  ('OOmm',  _integral('oiint', operator=r' \times ')),
    'OIIntCV': ('OOmm',  _integral('oiint', operator=r' \times ', vector=True)),
    'OIIntD':  ('OOmm',  _integral('oiint', operator=r' \cdot ')),
    'OIIntDV': ('OOmm',  _integral('oiint', operator=r' \cdot ', vector=True)),
    'IIInt':   ('OOmmmm', _integral('iiint')),
    'IIIntV':  ('OOmm',  _integral('iiint', power='^{3}')),
    'IIIntPV': ('OOmm',  _integral('iiint', power='^{3}', parens=True)),
    # -- aggregates ----------------------------------------------------------------------
    'Sum':               ('OOm', _aggregate(r'\sum')),
    'SumP':              ('OOm', _aggregate(r'\sum', parens=True)),
    'Product':           ('OOm', _aggregate(r'\prod')),
    'ProductP':          ('OOm', _aggregate(r'\prod', parens=True)),
    'CartesianProduct':  ('OOm', _aggregate(r'\bigtimes')),
    'CartesianProductP': ('OOm', _aggregate(r'\bigtimes', parens=True)),
    'Union':             ('OOm', _aggregate(r'\bigcup')),
    'UnionP':            ('OOm', _aggregate(r'\bigcup', parens=True)),
    'Intersection':      ('OOm', _aggregate(r'\bigcap')),
    'IntersectionP':     ('OOm', _aggregate(r'\bigcap', parens=True)),
    'Max':               ('Om',  lambda a: rf'\max{_limits(a[0], "")}{{{a[1]}}}'),
    'Min':               ('Om',  lambda a: rf'\min{_limits(a[0], "")}{{{a[1]}}}'),
    'Aggregate':         ('mOOm', lambda a: rf'{a[0]}{_limits(a[1], a[2])}{{{a[3]}}}'),
    'AggregateP':        ('mOOm', lambda a: rf'{a[0]}{_limits(a[1], a[2])}{{{_paren(a[3])}}}'),
    # -- derivatives ---------------------------------------------------------------------
    **{name: ('AOmm', _derivative(kind))
       for kind, names in (('Diff', ('Derivative', 'Drv')), ('PDiff', ('PDerivative', 'PDrv')),
                           ('FDiff', ('FDerivative', 'FDrv')), ('UDiff', ('UDerivative', 'UDrv')))
       for name in names},
    **{name: ('AOm', _derivative(kind, empty=True))
       for kind, names in (('Diff', ('DerivativeEmpty', 'DrvE')), ('PDiff', ('PDerivativeEmpty', 'PDrvE')),
                           ('FDiff', ('FDerivativeEmpty', 'FDrvE')), ('UDiff', ('UDerivativeEmpty', 'UDrvE')))
       for name in names},
    **{name: ('AOmm', _derivative(kind, parens=True))
       for kind, names in (('Diff', ('DerivativeParen', 'DrvP')), ('PDiff', ('PDerivativeParen', 'PDrvP')),
                           ('FDiff', ('FDerivativeParen', 'FDrvP')), ('UDiff', ('UDerivativeParen', 'UDrvP')))
       for name in names},
    'DerivativeEval':  ('Ommm', _derivative('Diff', evaluate=True)),
    'DrvEval':         ('Ommm', _derivative('Diff', evaluate=True)),
    'PDerivativeEval': ('Ommm', _derivative('PDiff', evaluate=True)),
    # -- statistics ----------------------------------------------------------------------
    'Expected':         ('mo', lambda a: rf'\mathrm{{E}}\left[{a[0]}\right]' + (rf'_{{{a[1]}}}' if a[1] else '')),
    'ExpectedE':        ('mo', lambda a: rf'\mathrm{{E}}\left[{a[0]}\right]' + (rf'_{{{a[1]}}}' if a[1] else '')),
    'ExpectedChevrons': ('mo', lambda a: rf'\left\langle {a[0]}\right\rangle' + (rf'_{{{a[1]}}}' if a[1] else '')),
    'Distribution':     ('mom', lambda a: rf'{a[0]}\left({a[1] + r" \mid " if a[1] else ""}{a[2]}\right)'),
    # -- sets, sequences, logs, nuclides, evaluation ---------------------------------------
    'Set': ('moo', lambda a: rf'\left\{{{a[0]}\right\}}' + (rf'_{{{a[1]}}}' if a[1] else '') + (rf'^{{{a[2]}}}' if a[2] else '')),
    'Seq': ('moo', lambda a: rf'\left({a[0]}\right)' + (rf'_{{{a[1]}}}' if a[1] else '') + (rf'^{{{a[2]}}}' if a[2] else '')),
    'Log': ('om', lambda a: r'\log' + (rf'_{{{a[0]}}}' if a[0] else '') + f'{{{a[1]}}}'),
    'Nuclide': ('OOm', lambda a: rf'{{}}^{{{a[0]}}}_{{{a[1]}}}\mathrm{{{a[2]}}}'),
    'Eval':  ('mmO', lambda a: rf'\left.{a[0]}\right|_{{{a[1]}}}' + (rf'^{{{a[2]}}}' if a[2] else '')),
    'EvalP': ('mmO', lambda a: rf'\left({a[0]}\right)_{{{a[1]}}}' + (rf'^{{{a[2]}}}' if a[2] else '')),
    'EvalB': ('mmO', lambda a: rf'\left[{a[0]}\right]_{{{a[1]}}}' + (rf'^{{{a[2]}}}' if a[2] else '')),
    # -- split lists -----------------------------------------------------------------------
    'Coord': ('Om', _split('[', ']', ';')),
    'Tuple': ('Om', _split('(', ')', ';')),
}

#: The four differentials take `^` and `_` in either order and neither is required, which is
#: what `e{^_}` means and what no MathJax macro can do.
_EMBELLISHED = re.compile(r'\\(' + '|'.join(DIFFERENTIAL) + r')(?![A-Za-z])')
_COMMAND = re.compile(r'\\(' + '|'.join(sorted(MACROS, key=len, reverse=True)) + r')(?![A-Za-z])')


def _embellishment(text: str, start: int) -> tuple[str, str, int]:
    """The `^{...}` and `_{...}` a differential may carry, in either order."""
    args, superscript, subscript = Arguments(text, start), '', ''
    while args.i < len(text) and text[args.i] in '^_':
        mark = text[args.i]
        args.i += 1
        value = args._balanced('{', '}')
        if value is None:
            value = text[args.i] if args.i < len(text) else ''
            args.i += 1
        if mark == '^':
            superscript = value
        else:
            subscript = value
    return superscript, subscript, args.i


def expand(text: str) -> str:
    r"""
    Every call to one of this repository's parsed macros, rewritten as plain TeX.

    Anything else is returned untouched, and a call whose arguments do not parse is left exactly
    as it was -- a visible `\Int` on the page beats a silently mangled integral.
    """
    text = _expand_differentials(text)
    out, i = [], 0
    while (found := _COMMAND.search(text, i)) is not None:
        name = found.group(1)
        signature, build = MACROS[name]
        reader = Arguments(text, found.end())
        arguments = reader.read(signature)
        if arguments is None:
            out.append(text[i:found.end()])
            i = found.end()
            continue
        out.append(text[i:found.start()])
        out.append(build(arguments))
        i = reader.i
    out.append(text[i:])
    return ''.join(out)


def _expand_differentials(text: str) -> str:
    out, i = [], 0
    while (found := _EMBELLISHED.search(text, i)) is not None:
        kind = found.group(1)
        superscript, subscript, after = _embellishment(text, found.end())
        reader = Arguments(text, after)
        body = reader.read('m')
        if body is None:
            out.append(text[i:found.end()])
            i = found.end()
            continue
        marks = (rf'^{{{superscript}}}' if superscript else '') + (rf'_{{{subscript}}}' if subscript else '')
        out.append(text[i:found.start()])
        out.append(rf'\mathop{{}}\!{_cs(DIFFERENTIAL[kind])}{marks}{body[0]}')
        i = reader.i
    out.append(text[i:])
    return ''.join(out)
