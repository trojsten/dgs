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

    @staticmethod
    def _quantum(printed: str) -> float | None:
        """The value of one unit in the last place of an already-formatted number."""
        mantissa, _, exponent = printed.lower().partition('e')
        if not mantissa.lstrip('-').replace('.', '').isdigit():
            return None                                 # not a plain number; leave it alone
        decimals = len(mantissa.partition('.')[2])
        try:
            return 10.0 ** ((int(exponent) if exponent else 0) - decimals)
        except ValueError:
            return None

    @classmethod
    def _outward(cls, endpoint: PhysicsQuantity, fmt: str, *, down: bool) -> PhysicsQuantity:
        """
        Move `endpoint` to the nearest printable value *away* from the other one.

        A range in this repository is the set of answers a marker accepts, so shrinking it
        rejects correct work. Rounding each end to nearest does shrink it: `29/bouncy-v` spans
        `[3.67749, 3.75]` metres and printed `3.7 – 3.8`, which excludes the very answer a solver
        using the exact `g` would hand in. Five of the nine intervals in phys were cut this way,
        `24/crane` among them, and the two that were not survived only because a `|w` happened to
        be generous enough.

        So the minimum is floored and the maximum ceiled, at whatever precision the format spec
        prints. With no precision nothing is dropped and this is a no-op.
        """
        import math
        printed = f'{endpoint.mag:{fmt}}' if fmt else None
        if printed is None:
            return endpoint
        quantum = cls._quantum(printed)
        if not quantum:
            return endpoint
        scaled = endpoint.mag / quantum
        # A value already on the grid must not be nudged off it by floating-point noise, so the
        # comparison gets a relative tolerance rather than an exact one.
        eps = 1e-9 * max(1.0, abs(scaled))
        rounded = math.floor(scaled + eps) if down else math.ceil(scaled - eps)
        return PhysicsQuantity.construct(rounded * quantum, endpoint.unit,
                                         si_extra=endpoint.si_extra)

    def __format__(self, fmt: str):
        minr = self._outward(self.minimum, fmt, down=True).format_struct(fmt)
        maxr = self._outward(self.maximum, fmt, down=False).format_struct(fmt)

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
