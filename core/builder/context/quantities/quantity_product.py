from core.utilities.dicts import strict_merge

from .physics_quantity import PhysicsQuantity


class QuantityProduct:
    """
    Represents a product of commensurate quantities (e.g. the dimensions of a box).
    """

    def __init__(self,
                 *qs: PhysicsQuantity):
        # First, try to force same units everywhere. If it works, good, if it does not, a pint error will be raised.
        assert len(qs) > 0, \
            f"{self.__class__.__name__} must have at least one quantity"
        self.qs = [q.to(qs[0].unit) for q in qs]

        self.si_extra = strict_merge(*(q.si_extra for q in self.qs))

    def __format__(self, fmt: str):
        fqs = [q.format_struct(fmt) for q in self.qs]
        self.magnitudes = ' x '.join([fq['magnitude'] for fq in fqs])

        si_extraf = PhysicsQuantity.format_si_extra(self.si_extra)
        magf = f'{{{self.magnitudes}}}'

        # Use \numproduct for dimensionless quantities, \qtyproduct otherwise.
        if fqs[0]['unit']:
            cmd = 'qtyproduct'
            unitf = f"{{{fqs[0]['unit']}}}"
        else:
            cmd = 'numproduct'
            unitf = ''
        return rf'\{cmd}{si_extraf}{magf}{unitf}'

    def __str__(self):
        return format(self, 'g')

    def __repr__(self):
        return f"{self.__class__.__name__} ({self.qs})"

    def __eq__(self, other):
        if isinstance(other, QuantityProduct):
            return self.qs == other.qs
        else:
            return NotImplemented

    def to(self, unit) -> "QuantityProduct":
        """ Convert all entries to another commensurate unit. """
        return QuantityProduct(*[q.to(unit) for q in self.qs])

    def __len__(self):
        return len(self.qs)

    def __iter__(self):
        return iter(self.qs)

    def __getitem__(self, index):
        return self.qs[index]
