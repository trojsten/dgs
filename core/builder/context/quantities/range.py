from core.builder.context.quantities.quantity import PhysicsQuantity


class QuantityRange:
    """
    Represents a range of two magnitudes of commensurate quantities.
    Primarily meant to be useful for result tolerances.
    """

    def __init__(self,
                 minimum: PhysicsQuantity,
                 maximum: PhysicsQuantity):
        self.minimum = minimum
        self.maximum = maximum
        self.si_extra = self.minimum.si_extra | self.maximum.si_extra

        assert self.minimum.unit == self.maximum.unit, \
            (f"Ranges can only be constructed from quantities with commensurate units,"
             f"got {self.minimum.unit} and {self.maximum.unit}")
        self.unit = self.minimum.unit


    def __str__(self):
        minr = self.minimum._struct_format()
        maxr = self.maximum._struct_format()

        minf = f'{{{minr['magnitude']}}}'
        maxf = f'{{{maxr['magnitude']}}}'
        unitf = f'{{{minr["unit"]}}}'
        siextraf = ', '.join(f'{key}={value}' for key, value in self.si_extra)
        siextraf = f'[{siextraf}]' if len(siextraf) >= 1 else siextraf

        cmd = 'qtyrange'
        return rf'\{cmd}{siextraf}{minf}{maxf}{unitf}'