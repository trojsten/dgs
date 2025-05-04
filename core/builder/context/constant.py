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

        if self.unit is not None:
            return rf"\qty{siextra}{{{value:{fmt}}}}{{{self.unit}}}"
        else:
            return rf"\num{siextra}{{{value:{fmt}}}}"

    def approximate(self, digits: int = None):
        """Return an approximate value of the constant.

        This is primarily useful for common rounded values, such as g = 10 m/s^2.

        Note that this representation might not be exact due to machien precision,
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
        return self.approximate()

    @property
    def full(self):
        return self.format()

    @property
    def full_approx(self):
        return self._format(self.approximate())

    @property
    def full_exact(self):
        return self._format(self.exact, 'g')

    def __str__(self):
        return self.full

    def __repr__(self):
        return self.full
