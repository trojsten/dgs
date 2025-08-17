import math
import numbers

from pint import UnitRegistry as u

from core.filters.numbers import cut_extra_one


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
    def construct(magnitude, unit):
        """
        Construct from magnitude and unit.
        """
        return PhysicsQuantity(u.Quantity(magnitude, unit)),

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
        super().__init__(quantity, **kwargs)

    def format(self, fmt: str = None):
        """Return a formatted string representation, by default a `g` one."""
        return self._format(self.value, fmt)

    def _format(self, value: float, fmt: str = None):
        if self.force_f:
            fmt = f'.{self.digits - 1}f'
        elif fmt is None:
            fmt = f'.{self.digits}g'
        siextra = '' if self.si_extra is None else f'[{self.si_extra}]'

        svalue = cut_extra_one(f'{value:{fmt}}')

        return f"{self.quantity:Lx}"

        if self.value.units == "":
            return rf"\num{siextra}{{{svalue}}}"
        elif self.value.units == u.radians:
            return rf"\ang{siextra}{{{svalue}}}"
        else:
            return rf"\qty{siextra}{{{svalue}}}{{{self.unit}}}"

    def approximate(self, digits: int = None):
        """
        Return an approximate value of the constant (not just formatted output, but truly rounded).
        This is primarily useful for common rounded values, such as g = 10 m/s^2 or m_e = 9.11e-31 kg.
        Note that this representation might not be exact due to machine precision,
        and will have to be passed through `format` again to render correctly.
        """
        if digits is None:
            digits = self.digits

        if self.value == 0:
            logarithm = 1
        else:
            logarithm = math.floor(math.log10(abs(self.value)))

        precision = digits - logarithm - 1
        return math.trunc(self.value * (10 ** precision) + 0.5) / (10 ** precision)

    @property
    def approx(self):
        """
        Property for approximated values.
        Use as (* const.name.approx *)
        """
        return self.approximate()

    @property
    def full(self):
        r"""
        Property for full, default-formatted values.
        Use as (* const.name.full *). This will render
        ```
        constant:
            value: 1.2345e-6
            unit: "\\kilo\\gram"
            digits: 3
        ```
        as \qty{1.23e-6}{\kilo\gram}.
        """
        return self.format()

    def fullf(self, precision: int = None) -> str:
        """
        Full, with f formatting
        """
        if precision is None:
            precision = self.digits
        return self.format(f'.{precision}f')

    def fullg(self, precision: int = 3) -> str:
        """
        Full, with g formatting
        """
        if precision is None:
            precision = self.digits
        return self.format(f'.{precision}g')

    @property
    def equals(self) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self.symbol} = {self.full}"

    @property
    def equalsf(self) -> str:
        """
        Full form with symbol and equal sign,
        `<symbol> = <full>`
        """
        return rf"{self.symbol} = {self.format('f')}"

    @property
    def deg(self) -> str:
        assert self.unit == r'\radian', \
            f"Only angles can be converted to degrees, got {self.unit}"
        return rf"\ang{{{math.degrees(self.value):{self.digits}f}}}"

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

    def __add__(self, other):
        if self.unit == other.unit:
            return PhysicsConstant(name="computed", value=self.value + other.value, unit=self.unit)
        else:
            raise ValueError("Cannot add constants: incompatible units")

    def __sub__(self, other):
        if self.unit == other.unit:
            return PhysicsConstant(name="computed", value=self.value - other.value, unit=self.unit)
        else:
            raise ValueError("Cannot add constants: incompatible units")

    def __mul__(self, value):
        if isinstance(value, numbers.Number):
            return PhysicsConstant(name="computed", value=self.value * value, unit=self.unit)
        else:
            raise NotImplementedError("Currently it is only possible to multiply constants by scalars")

    def __truediv__(self, value):
        if isinstance(value, numbers.Number):
            return PhysicsConstant(name="computed", value=self.value / value, unit=self.unit)
        else:
            raise NotImplementedError("Currently it is only possible to divide constants by scalars")
