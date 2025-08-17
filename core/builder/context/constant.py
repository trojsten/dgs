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

    def _format(self, fmt: str = None):
        if self.force_f:
            fmt = f'.{self.digits}f'
        elif fmt is None:
            fmt = f'.{self.digits}g'
        siextra = '' if self.si_extra is None else f'[{self.si_extra}]'

        svalue = cut_extra_one(f'{self.value:{fmt}}')

        return f"{self.quantity:Lx}"

        if self.value.units == "":
            return rf"\num{siextra}{{{svalue}}}"
        elif self.value.units == u.radians:
            return rf"\ang{siextra}{{{svalue}}}"
        else:
            return rf"\qty{siextra}{{{svalue}}}{{{self.unit}}}"

    @property
    def approx(self):
        """
        Property for approximated values.
        Use as (* const.name.approx *)
        """
        return self.approximate(self.digits)

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


    def fullg(self, precision: int = None) -> str:
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

