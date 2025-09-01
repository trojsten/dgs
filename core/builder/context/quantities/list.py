import functools
import operator

from core.builder.context.quantities.quantity import PhysicsQuantity


class QuantityList:
    """
    Represents a list of commensurate quantities.
    """

    def __init__(self,
                 *qs: list[PhysicsQuantity]):
        self.qs = qs
        self.si_extra = functools.reduce(operator.or_, [q.si_extra for q in self.qs])

        unique_units = set([q.unit for q in self.qs])
        assert len(unique_units) == 1, \
            f"Lists can only be constructed from a list of commensurate quantities, got {unique_units}"

    def __str__(self):
        cmd = 'qtylist'
        fqs = [q._struct_format() for q in self.qs]
        self.magnitudes = ';'.join([fq['magnitude'] for fq in fqs])

        unitf = f'{{{fqs[0]['unit']}}}'
        siextraf = ', '.join(f'{key}={value}' for key, value in self.si_extra)
        siextraf = f'[{siextraf}]' if len(siextraf) >= 1 else siextraf
        magf = f'{{{self.magnitudes}}}'

        return rf'\{cmd}{siextraf}{magf}{unitf}'

