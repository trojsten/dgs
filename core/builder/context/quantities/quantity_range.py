from typing import Self

from core.utilities.dicts import strict_merge

from .physics_quantity import PhysicsQuantity


class QuantityRange:
    """
    Represents a range of two magnitudes of commensurate quantities.
    Also meant to be useful for result tolerances.
    """

    def __init__(self,
                 minimum: PhysicsQuantity,
                 maximum: PhysicsQuantity):
        # Coerce to a common unit before comparing magnitudes, so ranges like
        # QuantityRange(1 kg, 500 g) work correctly. Incompatible units raise
        # the underlying pint DimensionalityError.
        self.minimum = minimum
        self.unit = minimum.unit
        self.maximum = maximum.to(self.unit)

        if self.minimum.mag > self.maximum.mag:
            raise ValueError(
                f"QuantityRange minimum ({minimum}) "
                f"must not exceed maximum ({maximum})"
            )

        self.si_extra = strict_merge(self.minimum.si_extra, self.maximum.si_extra)

    def __format__(self, fmt: str):
        minr = self.minimum.format_struct(fmt)
        maxr = self.maximum.format_struct(fmt)

        si_extraf = PhysicsQuantity.format_si_extra(self.si_extra)
        minf = f"{{{minr['magnitude']}}}"
        maxf = f"{{{maxr['magnitude']}}}"

        # Use \numrange for dimensionless quantities, \qtyrange otherwise.
        if minr['unit']:
            cmd = 'qtyrange'
            unitf = f"{{{minr['unit']}}}"
        else:
            cmd = 'numrange'
            unitf = ''
        return rf'\{cmd}{si_extraf}{minf}{maxf}{unitf}'

    def widen(self, value: float) -> Self:
        """
        Return a new range whose width is multiplied by ``(1 + value)``,
        expanded symmetrically around the centre.

        For a range ``[a, b]`` with centre ``c = (a + b) / 2`` and half-width
        ``h = (b - a) / 2``, the result is ``[c - h*(1+v), c + h*(1+v)]``.

        This always widens (never narrows) regardless of sign:
            [1, 3]   widen(0.1) -> [0.9, 3.1]
            [-3, -1] widen(0.1) -> [-3.1, -0.9]
            [-1, 1]  widen(0.5) -> [-1.5, 1.5]

        A degenerate range (a == b) stays degenerate, since its half-width
        is zero. Construct an explicit non-degenerate range first if you
        want a tolerance band around a single value.

        This should be useful for specifying ranges of acceptable results
        in Náboj.
        """
        assert value >= 0, f"widen factor must be non-negative, got {value}"
        centre = (self.minimum + self.maximum) * 0.5
        half_width = (self.maximum - self.minimum) * 0.5 * (1 + value)
        return QuantityRange(centre - half_width, centre + half_width)

    def to(self, unit) -> Self:
        """ Convert both endpoints to another commensurate unit. """
        return QuantityRange(self.minimum.to(unit), self.maximum.to(unit))

    def __str__(self):
        return format(self, 'g')
