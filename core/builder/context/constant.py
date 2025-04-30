from enschema import Schema


class PhysicsConstant:
    def __init__(self, name, **kwargs):
        self.name = name
        self.value = float(kwargs['value'])
        self.exact = float(kwargs.get('exact', self.value))
        self.unit = kwargs.get('unit', None)
        self.digits = kwargs.get('digits', 3)
        self.si_extra = kwargs.get('siextra', None)

    @property
    def full(self):
        return self.format()

    def format(self, fmt: str = None):
        if fmt is None:
            fmt = f'.{self.digits}g'
        siextra = '' if self.si_extra is None else f'[{self.si_extra}]'
        return rf"\qty{siextra}{{{self.exact:{fmt}}}}{{{self.unit}}}"

    def __str__(self):
        return self.full

    def __repr__(self):
        return self.full
