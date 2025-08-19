import math

from pint import UnitRegistry as u

from core.builder.context.quantity import PhysicsQuantity
from core.filters.hacks import cut_extra_one


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
        magnitude = kwargs.pop('value') # FixMe
        unit = kwargs.pop('unit')
        return PhysicsConstant(name, u.Quantity(magnitude, unit), **kwargs)

    def format(self, fmt: str = None):
        if self.force_f:
            fmt = f'.{self.digits}f'
        elif fmt is None:
            fmt = f'.{self.digits}g'

        return self._format(fmt, si_extra=self.si_extra)

    @property
    def approx(self):
        """
        Property for approximated values.
        Use as (* const.name.approx *)
        """
        return self.approximate(self.digits)

    def fullg(self, precision: int = None) -> str:
        """
        Full, with g formatting
        """
        if precision is None:
            precision = self.digits
        return self.format(f'.{precision}g')

    @property
    def full_exact(self):
        return self._format(self.value, '99g')

    @property
    def full_approx(self):
        return self._format(self.approximate())

    @property
    def full_value(self):
        r"""
        Property for full, exact values.
        Use as (* const.name.full_value *). This will render
        ```
        title:
            value: 1.2345e-6
            unit: "\\kilo\\gram"
            digits: 3
        ```
        as \qty{1.2345e-6}{\kilo\gram} regardless of `digits`.
        """
        return self._format(self.quantity.magnitude, '.15g')

    def __str__(self):
        return self.full

    def __repr__(self):
        return self.full

