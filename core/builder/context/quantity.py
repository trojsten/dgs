import math
import numbers
from typing import Optional

from pint import UnitRegistry as u


class PhysicsQuantity:
    """
    Represents a physics quantity for comfortable and reproducible use in calculations and texts.
    """

    def __init__(self,
                 quantity: u.Quantity,
                 *,
                 symbol: str = None,
                 si_extra: str = None,
                 force_f: bool = False):
        self.quantity = quantity
        self.symbol = symbol
        self.si_extra = si_extra
        self.force_f = force_f

    @staticmethod
    def construct(magnitude, unit, **kwargs):
        """
        Construct from magnitude and unit.
        """
        return PhysicsQuantity(u.Quantity(magnitude, unit), **kwargs)

    def __add__(self, other):
        return PhysicsQuantity(self.quantity + other.quantity)

    def __radd__(self, other):
        return other + self

    def __sub__(self, other):
        return PhysicsQuantity(self.quantity - other.quantity)

    def __rsub__(self, other):
        return other - self

    def __mul__(self, other):
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(self.quantity * other.quantity)
        elif isinstance(other, numbers.Number):
            return PhysicsQuantity(self.quantity * other)
        else:
            return NotImplemented

    def __rmul__(self, other):
        return other * self

    def __truediv__(self, other):
        if isinstance(other, PhysicsQuantity):
            return PhysicsQuantity(self.quantity / other.quantity)
        elif isinstance(other, numbers.Number):
            return PhysicsQuantity(self.quantity / other)
        else:
            return NotImplemented

    def __str__(self):
        return str(self.quantity)

    @property
    def mag(self):
        """ Return the internal magnitude. """
        return self.quantity.magnitude

    @property
    def unit(self):
        """ Return the internal unit. """
        return self.quantity.units

    def approximate(self, digits: int):
        """
        Return an approximate value of the constant (not just formatted output, but truly rounded).
        This is primarily useful for common rounded values, such as g = 10 m/s^2 or m_e = 9.11e-31 kg.
        Note that this representation might not be exact due to machine precision,
        and will have to be passed through `format` again to render correctly.
        """
        if self.quantity.magnitude == 0:
            logarithm = 1
        else:
            logarithm = math.floor(math.log10(abs(self.quantity.magnitude)))

        precision = digits - logarithm - 1
        magnitude = math.trunc(self.quantity.magnitude * (10 ** precision) + 0.5) / (10 ** precision)

        return PhysicsQuantity(u.Quantity(magnitude, self.quantity.units))

    def format(self, fmt: str = None):
        """Return a formatted string representation, by default a `g` one."""
        return f"{self.quantity:Lx}"

    def fullf(self, precision: int = None) -> str:
        """
        Full, with f formatting
        """
        if precision is None:
            precision = self.digits
        return self.format(f'.{precision}f')

    def to(self, new_unit: str):
        self.quantity = self.quantity.to(new_unit)
        return self