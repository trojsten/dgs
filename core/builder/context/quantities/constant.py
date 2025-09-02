from pint import UnitRegistry as u

from core.builder.context.quantities.quantity import PhysicsQuantity


class PhysicsConstant(PhysicsQuantity):
    """
    Represents a stored physical constant for comfortable and reproducible use in texts.
    """
    def __init__(self,
                 name: str,
                 quantity: u.Quantity,
                 **kwargs):
        self.name = name
        self.digits = kwargs.pop('digits', 3)
        self.aliases = kwargs.pop('aliases', [])
        self.exact = kwargs.pop('exact', False)
        super().__init__(quantity, **kwargs)

    @staticmethod
    def construct(name, **kwargs):
        magnitude = kwargs.pop('magnitude')
        unit = kwargs.pop('unit')
        return PhysicsConstant(name, u.Quantity(magnitude, unit), **kwargs)

    def format(self, fmt: str = None):
        if self.force_f:
            fmt = f'.{self.digits}f'
        elif fmt is None:
            fmt = f'.{self.digits}g'

        return self._format(fmt)

    @property
    def approx(self):
        """
        Property for approximated values.
        Use as (* const.name.approx *)
        """
        return self.approximate(self.digits)

    def _full(self, kind: str, precision: int = None) -> str:
        if precision is None:
            precision = self.digits
        return self._format(f'.{precision}{kind}')

    def fullf(self, precision: int = None) -> str:
        """ Full, with f formatting """
        return self._full('f', precision)

    def fullg(self, precision: int = None) -> str:
        """ Full, with g formatting """
        return self._full('g', precision)

    @property
    def full_exact(self):
        return self._format('99g')

    @property
    def full_approx(self):
        return self._format(self.approximate(self.digits))

    def __str__(self):
        return self.full

    def __repr__(self):
        return self.full

