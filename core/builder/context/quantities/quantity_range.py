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
    def _quantum_exponent(printed: str) -> int | None:
        """
        `e` such that one unit in the last place of an already-formatted number is `10**e`.

        The exponent rather than the value, because the endpoint is rebuilt by scaling an
        integer by it and `10.0 ** -7` is not exactly a ten-millionth. Multiplying by the float
        left `5.6789012` as `5.678901199999999`, which the old six-decimal formatting hid and
        the natural one prints in full.
        """
        mantissa, _, exponent = printed.lower().partition('e')
        if not mantissa.lstrip('-').replace('.', '').isdigit():
            return None                                 # not a plain number; leave it alone
        decimals = len(mantissa.partition('.')[2])
        try:
            return (int(exponent) if exponent else 0) - decimals
        except ValueError:
            return None

    @classmethod
    def _quantum(cls, printed: str) -> float | None:
        """One unit in the last place, as a value. Kept for callers that want the size."""
        e = cls._quantum_exponent(printed)
        return None if e is None else 10.0 ** e

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
        from decimal import Decimal

        from core.filters.hacks import BareKind, natural
        # The grid has to be the last place the endpoint *actually prints*, so this must format
        # it the way `format_struct` does. A bare `f` or `e` no longer means six decimals, and
        # reading the grid off `1.234000` while printing `1.234` would put the band's last digit
        # outside the grid that was supposed to contain it.
        printed = (natural(endpoint.mag, fmt) if BareKind.match(fmt or '')
                   else f'{endpoint.mag:{fmt}}') if fmt else None
        if printed is None:
            return endpoint
        exponent = cls._quantum_exponent(printed)
        if exponent is None:
            return endpoint
        scaled = endpoint.mag / 10.0 ** exponent
        # A value already on the grid must not be nudged off it by floating-point noise, so the
        # comparison gets a relative tolerance rather than an exact one.
        eps = 1e-9 * max(1.0, abs(scaled))
        rounded = math.floor(scaled + eps) if down else math.ceil(scaled - eps)
        # Scaled through `Decimal`, which is exact for a power of ten: the endpoint lands on the
        # grid rather than a float's-breadth away from it.
        value = float(Decimal(rounded).scaleb(exponent))
        return PhysicsQuantity.construct(value, endpoint.unit, si_extra=endpoint.si_extra)

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

    def snap(self, quantum: float) -> Self:
        """
        Round the ends outward onto a grid of `quantum`, in this range's own unit.

        `__format__` already moves each end outward to the last place it prints, which is what
        keeps the printed band from rejecting a correct answer. This is the same operation with
        the grid chosen rather than inferred, and it exists because the format spec cannot ask
        for one coarser than a whole unit: `.0f` is as far as it goes, and an answer good to
        four figures in kilometres needs ten.

        `08/same-parallel` is the case. Its band runs 11555 - 11569 km across the two Earth
        radii, and a solver who takes the 6378 km their school taught gets 11568.7 and writes
        11570. Snapping to 10 km prints 11550 - 11570 and accepts them. That is not padding:
        the endpoints do not move by a chosen margin, they move onto the precision the answer
        is actually good to, and the band still contains exactly the admissible values.

        **Not `widen`.** `widen` multiplies the width by a factor of someone's choosing, which
        is how `29/bouncy-v` came to hide a rounding defect rather than fix it. This moves each
        end to the next grid point and no further, and snapping an already-snapped range is a
        no-op.
        """
        import math
        assert quantum > 0, f"snap quantum must be positive, got {quantum}"
        eps = 1e-9 * max(1.0, abs(self.minimum.mag / quantum), abs(self.maximum.mag / quantum))
        low = math.floor(self.minimum.mag / quantum + eps) * quantum
        high = math.ceil(self.maximum.mag / quantum - eps) * quantum
        return self.__class__(
            PhysicsQuantity.construct(low, self.minimum.unit, si_extra=self.minimum.si_extra),
            PhysicsQuantity.construct(high, self.maximum.unit, si_extra=self.maximum.si_extra),
        )

    def to(self, unit) -> Self:
        """ Convert both endpoints to another commensurate unit. """
        return QuantityRange(self.minimum.to(unit), self.maximum.to(unit))

    def __str__(self):
        return format(self, 'g')
