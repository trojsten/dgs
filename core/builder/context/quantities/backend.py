r"""
How a quantity spells itself, as a choice rather than a hard-coded one.

`PhysicsQuantity.__format__` used to return `\qty{3}{\metre\per\second}` and nothing else could,
so presentation was produced at the point the value was created. That is the thing every
non-LaTeX consumer has had to undo: `core/filters/siunitx.py` is 317 lines whose only job is to
parse those calls back apart for MathJax, and it exists because **pandoc cannot carry them**.
Measured, not assumed -- `pandoc --to typst` turns `A quantity: \qty{3}{\metre}.` into
`A quantity: .`, and `--to html` does the same. Standard maths converts cleanly and figures and
equations survive with their crossref labels; siunitx is a package macro, so it is raw TeX to
pandoc and raw TeX is dropped. Silently.

So the spelling moves here, behind two implementations.

**The backend belongs to the render, not to the quantity.** It is read at format time rather than
stored on the object, and that is deliberate twice over. A quantity's identity does not depend on
who prints it -- putting the backend on the instance would put presentation back into the value,
which is the whole thing being undone. And `PhysicsQuantity` creates new instances all through
its arithmetic: `_binop`, `_unop` and eleven numpy wrappers. An attribute would have to be
threaded through every one of them, which is exactly how `exact` came to be laundered by
`__neg__`, `__abs__` and `__rtruediv__` for years. Ambient state has a cost; a propagation
obligation across twenty constructors has a worse one, and a demonstrated failure.

`|txt` is then not a parallel implementation but a call that asks for the other backend, which is
what makes the two legible as alternatives instead of as two routes that happen to agree.

**One difference is not really about the backend**, and it is flagged rather than hidden:
`rounds_outward`. A range printed by LaTeX is `answer-interval.md`, the set of answers a marker
accepts, so its ends move outward to the last place they print -- rounding to nearest would shrink
the set and turn away correct work, which is the `29/bouncy-v` defect. A range printed as plain
text is a label on a span in a drawing, and widening it would claim a width nobody measured. That
is a distinction between *purposes* that happens to line up with the backends today. If a drawing
ever has to carry an interval, this is the flag that has to stop riding on the backend.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import ClassVar

#: pint's "pretty" spec: `~` picks the short symbol over the full name (`m`, not `meter`) and `P`
#: gives Unicode superscripts, `/` and `⋅`.
PINT_PRETTY = '~P'

#: pint's short symbol for a plane angle -- the one unit that closes up against its number.
PINT_DEGREE = 'deg'

SUPERSCRIPT = str.maketrans('0123456789-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻')


def superscript_exponent(printed: str) -> str:
    """
    `6.674e-11` becomes `6.674×10⁻¹¹`; a number with no exponent is returned untouched.

    `cut_extra_one` has already turned `1e+15` into `e+15`, so that siunitx sets `10^{15}` rather
    than `1 · 10^{15}`. The same is wanted here: an empty mantissa gives `10¹⁵`, with no stray
    `×` in front of it.
    """
    mantissa, separator, exponent = printed.partition('e')
    if not separator:
        return printed

    sign = '-' if exponent.startswith('-') else ''
    digits = exponent.lstrip('+-').lstrip('0') or '0'
    power = f'10{(sign + digits).translate(SUPERSCRIPT)}'
    return f'{mantissa}×{power}' if mantissa else power


class Backend:
    """
    One way of spelling quantities.

    Four questions, which is all the difference between the two amounts to: how a unit is
    written, how a single value is written, how several are written together, and whether a
    range rounds outward.
    """
    name: str = None
    rounds_outward: bool = True

    def unit(self, quantity) -> str:
        """The unit alone, spelled for this backend. Empty for a dimensionless quantity."""
        raise NotImplementedError

    def scalar(self, magnitude: str, unit: str, si_extra: dict) -> str:
        """One magnitude and its unit."""
        raise NotImplementedError

    def aggregate(self, kind: str, magnitudes: list[str], unit: str, si_extra: dict) -> str:
        """Several commensurate magnitudes: `kind` is `range`, `list` or `product`."""
        raise NotImplementedError

    def bare_unit(self, unit: str, si_extra: dict) -> str:
        """A unit with no number in front of it, which is what `|unit` asks for."""
        raise NotImplementedError


class LatexBackend(Backend):
    r"""siunitx, which is how a value reaches the booklet."""
    name = 'latex'
    rounds_outward = True

    #: How siunitx wants several magnitudes *handed to it*, which is not what it prints. A range
    #: takes two brace groups instead and so is absent here. What reaches the page is set by
    #: `list-separator` and friends in `core/latex/siunitx.tex`.
    INPUT_SEPARATORS: ClassVar[dict[str, str]] = {'list': ';', 'product': ' x '}

    @staticmethod
    def _options(si_extra: dict) -> str:
        options = ', '.join(f'{key}={value}' for key, value in si_extra.items())
        return f'[{options}]' if options else ''

    def unit(self, quantity) -> str:
        return quantity.latex_unit()

    def scalar(self, magnitude: str, unit: str, si_extra: dict) -> str:
        options = self._options(si_extra)
        # An angle on its own is `\ang`, siunitx's own command for one, and what the sources
        # write by hand throughout. Only a bare degree: `\qty{30}{\degree\per\second}` is a
        # rate, not an angle.
        if unit == r'\degree':
            return rf'\ang{options}{{{magnitude}}}'
        command = 'qty' if unit else 'num'
        return rf'\{command}{options}{{{magnitude}}}' + (f'{{{unit}}}' if unit else '')

    def aggregate(self, kind: str, magnitudes: list[str], unit: str, si_extra: dict) -> str:
        r"""
        `\qtyrange[opts]{1}{2}{\metre}` and its five siblings.

        A range passes two brace groups; a list and a product pass one, their magnitudes already
        joined by the separator siunitx *parses* -- `;` and ` x `. What it prints is set in
        `core/latex/siunitx.tex`, by `range-phrase`, `list-separator` and the rest.

        An empty unit gives `\num…` and omits the trailing group rather than passing `{}`:
        siunitx reads an empty unit as a unit and sets the number followed by nothing.
        """
        groups = (magnitudes if kind == 'range'
                  else [self.INPUT_SEPARATORS[kind].join(magnitudes)])
        command = ('qty' if unit else 'num') + kind
        body = ''.join(f'{{{group}}}' for group in groups)
        return rf'\{command}{self._options(si_extra)}{body}' + (f'{{{unit}}}' if unit else '')

    def bare_unit(self, unit: str, si_extra: dict) -> str:
        return rf'\unit{self._options(si_extra)}{{{unit or "1"}}}'


class PlainBackend(Backend):
    r"""
    Plain text, for the formats that have no TeX to typeset with.

    A drawing has no xelatex step -- `rsvg-convert` puts SVG text on the page with a system font
    -- so a `\qty{}{}` inside an `.svg` prints its own backslashes. This writes `3 m/s` instead.

    The unit comes from **pint's own spec** rather than a table here, which is the point worth
    keeping: a table of ours would have to carry every unit the sources use and would drift from
    the registry the values are built in. pint's comes out of that registry by construction, so a
    unit that can be computed can be printed. The LaTeX side cannot do this -- siunitx macros are
    not pint's names -- and that asymmetry is why `PINT_TO_SIUNITX` exists on only one of them.
    """
    name = 'plain'
    rounds_outward = False

    #: What goes between the parts of a range, a list and a product. Taken from the siunitx
    #: settings in `core/latex/siunitx.tex` rather than chosen here, because this backend's job
    #: is to print what the booklet prints: `range-phrase` is an en dash with spaces around it,
    #: `list-separator` a comma and a space.
    SEPARATORS: ClassVar[dict[str, str]] = {'range': ' – ', 'list': ', ',
                                            'product': ' × '}

    def unit(self, quantity) -> str:
        return format(quantity.unit, PINT_PRETTY)

    def scalar(self, magnitude: str, unit: str, si_extra: dict) -> str:
        magnitude = superscript_exponent(magnitude)
        if unit == PINT_DEGREE:
            return f'{magnitude}°'
        return f'{magnitude} {unit}' if unit else magnitude

    def aggregate(self, kind: str, magnitudes: list[str], unit: str, si_extra: dict) -> str:
        """
        Every element written out in full, unit and all.

        `list-units` and `range-units` are both `repeat` in `core/latex/siunitx.tex`, so the
        booklet prints `3 cm × 4 cm × 5 cm` and this prints the same.
        """
        return self.SEPARATORS[kind].join(
            self.scalar(magnitude, unit, si_extra) for magnitude in magnitudes)

    def bare_unit(self, unit: str, si_extra: dict) -> str:
        return unit


LATEX = LatexBackend()
PLAIN = PlainBackend()

#: Read at format time. A `ContextVar` rather than a module global so that the editor, which
#: renders in-process under Flask, cannot have one request's backend leak into another's.
_CURRENT: ContextVar[Backend] = ContextVar('dgs_quantity_backend', default=LATEX)

BACKENDS = {backend.name: backend for backend in (LATEX, PLAIN)}


def current() -> Backend:
    return _CURRENT.get()


def resolve(backend) -> Backend:
    """A `Backend`, or the name of one. Unknown names fail here rather than at the page."""
    if isinstance(backend, Backend):
        return backend
    try:
        return BACKENDS[backend]
    except KeyError:
        raise ValueError(f"Unknown quantity backend {backend!r}; "
                         f"expected one of {sorted(BACKENDS)}") from None


def set_current(backend) -> None:
    """Choose the backend for the rest of this render. `build_render_context` calls this."""
    _CURRENT.set(resolve(backend))


@contextmanager
def using(backend):
    """The backend for one expression, which is what `|txt` is."""
    token = _CURRENT.set(resolve(backend))
    try:
        yield
    finally:
        _CURRENT.reset(token)
