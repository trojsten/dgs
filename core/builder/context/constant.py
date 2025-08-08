import math
import numbers

from core.filters.numbers import cut_extra_one


class PhysicsConstant:
    """
    Represents a stored physical constant for comfortable and reproducible use in texts.
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self.value = float(kwargs['value'])
        self.unit = kwargs.get('unit', None)
        self.digits = kwargs.get('digits', 3)
        self.aliases = kwargs.get('aliases', [])
        self.si_extra = kwargs.get('siextra', None)
        self.force_f: bool = kwargs.get('force_f', False)

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

        if self.unit is None:
            return rf"\num{siextra}{{{svalue}}}"
        elif self.unit == r"\degree":
            return rf"\ang{siextra}{{{svalue}}}"
        else:
            return rf"\qty{siextra}{{{svalue}}}{{{self.unit}}}"

    def approximate(self, digits: int = None):
        """
        Return an approximate value of the constant (not just formatted output, but truly rounded).
        This is primarily useful for common rounded values, such as g = 10 m/s^2 or m_e = 9.11e-31 kg.
        Note that this representation might not be value due to machine precision,
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
        if precision is None:
            precision = self.digits
        return self.format(f'.{precision}f')

    def fullg(self, precision: int = 3) -> str:
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
        return self._format(self.value, '.15g')

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
