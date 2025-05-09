import math


class PhysicsConstant:
    def __init__(self, name, **kwargs):
        self.name = name
        self.value = float(kwargs['value'])
        self.exact = float(kwargs.get('exact', self.value))
        self.unit = kwargs.get('unit', None)
        self.digits = kwargs.get('digits', 3)
        self.si_extra = kwargs.get('siextra', None)

    def format(self, fmt: str = None):
        """Return a formatted string representation, by default a `g` one."""
        return self._format(self.exact, fmt)

    def _format(self, value: float, fmt: str = None):
        if fmt is None:
            fmt = f'.{self.digits}g'
        siextra = '' if self.si_extra is None else f'[{self.si_extra}]'

        if self.unit is None:
            return rf"\num{siextra}{{{value:{fmt}}}}"
        elif self.unit == r"\degree":
            return rf"\ang{siextra}{{{value:{fmt}}}}"
        else:
            return rf"\qty{siextra}{{{value:{fmt}}}}{{{self.unit}}}"

    def approximate(self, digits: int = None):
        """
        Return an approximate value of the constant (not just formatted output, but truly rounded).
        This is primarily useful for common rounded values, such as g = 10 m/s^2 or m_e = 9.11e-31 kg.
        Note that this representation might not be exact due to machine precision,
        and will have to be passed through `format` again to render correctly.
        """
        if digits is None:
            digits = self.digits


        if self.exact == 0:
            logarithm = 1
        else:
            logarithm = int(-math.log10(abs(self.exact)))

        return math.trunc(self.exact * (10 ** (digits + logarithm)) + 0.5) / (10 ** (digits + logarithm))

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

    @property
    def full_approx(self):
        return self._format(self.approximate())

    @property
    def full_exact(self):
        r"""
        Property for full, exact values.
        Use as (* const.name.full_exact *). This will render
        ```
        constant:
            value: 1.2345e-6
            unit: "\\kilo\\gram"
            digits: 3
        ```
        as \qty{1.2345e-6}{\kilo\gram} regardless of `digits`.
        """
        return self._format(self.exact, '.15g')

    def __str__(self):
        return self.full

    def __repr__(self):
        return self.full
