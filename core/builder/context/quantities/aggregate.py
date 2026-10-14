r"""
What a range, a list and a product have in common, which turned out to be nearly everything.

`QuantityList` and `QuantityProduct` were the same class written twice -- identical `__init__`,
`si_extra`, `to`, `__eq__`, `__str__`, `__repr__`, `__len__`, `__iter__` and `__getitem__`, and
`__format__`s differing in exactly two things: the string the magnitudes are joined with, and the
siunitx command stem. `QuantityRange` is the third sibling and the one with real differences --
two endpoints rather than a sequence, outward rounding, `snap` -- but it assembles its output the
same way.

So two levels. `QuantityAggregate` holds the assembly and the things every aggregate has;
`QuantitySequence` adds the "several commensurate quantities in a row" behaviour that the list and
the product share and the range does not. Each concrete class is then a name, a stem and, for the
two sequences, a separator.

**The assembly is the piece a second backend will replace**, and collecting it here is why this
refactor comes first: `\qtylist{...}{...}` is a siunitx call that pandoc drops silently on any
writer but LaTeX -- `\qty{3}{\metre}` converts to Typst as nothing at all, and to HTML as nothing
at all, which is why `core/filters/siunitx.py` exists. Three copies of that call site would be
three places to teach about a backend. There is one.
"""
from core.utilities.dicts import strict_merge

from .physics_quantity import PhysicsQuantity


class QuantityAggregate:
    """Several quantities printed as one siunitx call."""

    #: The siunitx command stem: `range`, `list` or `product`. The prefix is chosen per call,
    #: because siunitx spells the dimensionless form differently -- `\numlist` against `\qtylist`
    #: -- and whether there is a unit is a property of the values, not of the class.
    _KIND: str = None

    def _assemble(self, groups: list[str], unit: str) -> str:
        r"""
        `\qtyrange[opts]{1}{2}{\metre}` and its five siblings, from parts already formatted.

        `groups` are the brace groups before the unit: one joined string for a list or a product,
        two endpoints for a range. The unit decides the command, so an empty one gives `\num…`
        and omits the trailing group altogether rather than passing `{}` -- siunitx reads an
        empty unit as a unit, and sets the number followed by nothing where it would have gone.
        """
        command = ('qty' if unit else 'num') + self._KIND
        si_extra = PhysicsQuantity.format_si_extra(self.si_extra)
        body = ''.join(f'{{{group}}}' for group in groups)
        return rf'\{command}{si_extra}{body}' + (f'{{{unit}}}' if unit else '')

    def __str__(self):
        return format(self, 'g')


class QuantitySequence(QuantityAggregate):
    """
    An arbitrary number of commensurate quantities, printed in one call with a separator.

    The separator is siunitx's own input syntax rather than what reaches the page: `;` between
    list items and ` x ` between product factors is what `\\qtylist` and `\\qtyproduct` *parse*.
    What they print is set in `core/latex/siunitx.tex` (`list-separator`, `inter-unit-product`
    and the rest), which is also where `core/filters/plain.py` copies its own separators from.
    """

    #: What the magnitudes are joined with on the way *in* to siunitx. Not a typographic choice.
    _SEPARATOR: str = None

    def __init__(self, *qs: PhysicsQuantity):
        # Force the same unit everywhere first; if that cannot be done, pint raises.
        assert len(qs) > 0, \
            f"{self.__class__.__name__} must have at least one quantity"
        self.qs = [q.to(qs[0].unit) for q in qs]
        self.si_extra = strict_merge(*(q.si_extra for q in self.qs))

    def __format__(self, fmt: str):
        formatted = [q.format_struct(fmt) for q in self.qs]
        # The unit is the first element's: the constructor has already coerced them all to it.
        return self._assemble([self._SEPARATOR.join(f['magnitude'] for f in formatted)],
                              formatted[0]['unit'])

    def to(self, unit):
        """Convert every element to another commensurate unit."""
        return self.__class__(*[q.to(unit) for q in self.qs])

    def __eq__(self, other):
        # `type` rather than `isinstance`, so that a list and a product of the same quantities
        # are not equal: they are different statements about them.
        if type(self) is type(other):
            return self.qs == other.qs
        return NotImplemented

    def __repr__(self):
        return f"{self.__class__.__name__} ({self.qs})"

    def __len__(self):
        return len(self.qs)

    def __iter__(self):
        return iter(self.qs)

    def __getitem__(self, index):
        return self.qs[index]
