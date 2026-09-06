import math

import pint
import pytest
import regex as re

from core.builder.context.quantities import (
    MissingSymbolError,
    PhysicsQuantity,
    QuantityList,
    QuantityProduct,
    QuantityRange,
    UnknownUnitMacroError,
)


@pytest.fixture
def mass1():
    return PhysicsQuantity.construct(1, 'kg', symbol='m_1')


@pytest.fixture
def mass2():
    return PhysicsQuantity.construct(7, 'kg', symbol='m_2')


@pytest.fixture
def mass_mega():
    return PhysicsQuantity.construct(96.7, 'kg', symbol='m_D')


@pytest.fixture
def mass_brutal():
    return PhysicsQuantity.construct(2e30, 'kg', symbol='m_Sun', si_extra={'forbid-literal-units': 'false'})


@pytest.fixture
def length1():
    return PhysicsQuantity.construct(2, 'm', symbol='L_1')


@pytest.fixture
def length2():
    return PhysicsQuantity.construct(320, 'cm', symbol='L_2')


class TestExpression:
    def test_sum(self, mass1, mass2):
        expected = PhysicsQuantity.construct(8000, 'gram')
        computed = (mass1 + mass2).to('gram')
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"


    def test_sum_fails(self, mass1, length1):
        with pytest.raises(pint.errors.DimensionalityError):
            _ = mass1 + length1


class TestAngles:
    def test_angle(self):
        first = PhysicsQuantity.construct(math.pi / 2, 'rad', symbol=r'\omega')
        second = PhysicsQuantity.construct(45, 'deg', symbol=r'\alpha')
        computed = first + second
        expected = PhysicsQuantity.construct(135, 'deg', symbol=r'\omega')
        assert expected == computed


class TestRange:
    def test_masses(self, mass1, mass2):
        expected = r'\qtyrange{1}{7}{\kilo\gram}'
        computed = rf'{QuantityRange(mass1, mass2)}'
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"

    def test_span(self, mass1, mass2):
        expected = r'\qtyrange{1}{7}{\kilo\gram}'
        computed = rf'{mass1 % mass2}'
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"

    def test_span_incommensurate(self, mass1, length1):
        with pytest.raises(pint.errors.DimensionalityError):
            _ = mass1 % length1


class TestRangeRoundsOutward:
    """
    A range in this repository is the set of answers a marker accepts, so a printed interval must
    contain the computed one. Rounding both ends to nearest can only shrink it: `29/bouncy-v`
    spans 3.67749 to 3.75 metres and used to print `3.7 – 3.8`, which excludes the answer a solver
    using the exact `g` would hand in. Five of the nine intervals in phys were cut that way.
    """

    @staticmethod
    def span(low, high, unit='metre'):
        return QuantityRange(PhysicsQuantity.construct(low, unit),
                             PhysicsQuantity.construct(high, unit))

    def test_the_minimum_is_floored(self):
        assert f'{self.span(3.67749375, 3.75):.1f}' == r'\qtyrange{3.6}{3.8}{\metre}'

    def test_the_maximum_is_ceiled(self):
        assert f'{self.span(2.4644, 2.51327):.2f}' == r'\qtyrange{2.46}{2.52}{\metre}'

    def test_the_printed_interval_contains_the_computed_one(self):
        """The property the whole thing exists for, checked at four precisions."""
        low, high = 0.427521, 0.440973
        for precision in range(1, 5):
            printed = f'{self.span(low, high):.{precision}f}'
            a, b = (float(x) for x in re.findall(r'\{([\d.]+)\}', printed)[:2])
            assert a <= low and b >= high, f'{precision}: {printed}'

    def test_an_endpoint_already_on_the_grid_is_not_nudged(self):
        """Floating-point noise must not turn 3.7 into 3.6, nor 3.8 into 3.9."""
        assert f'{self.span(3.7, 3.8):.1f}' == r'\qtyrange{3.7}{3.8}{\metre}'

    def test_whole_numbers_survive(self):
        assert f'{self.span(5560, 5570, "kilometre"):.0f}' == r'\qtyrange{5560}{5570}{\kilo\metre}'

    def test_no_precision_drops_nothing_and_so_changes_nothing(self):
        """With the bare spec the magnitude prints in full, so there is nothing to round away."""
        assert f'{self.span(3.67749375, 3.75)}' == r'\qtyrange{3.67749375}{3.75}{\metre}'

    def test_a_dimensionless_range_still_uses_numrange(self):
        assert f'{self.span(0.101, 0.209, ""):.1f}' == r'\numrange{0.1}{0.3}'


class TestList:
    def test_masses(self, mass1, mass2, mass_mega):
        expected = r'\qtylist{1;7;96.7}{\kilo\gram}'
        computed = rf'{QuantityList(mass1, mass2, mass_mega)}'
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"

    def test_masses_sun(self, mass1, mass2, mass_brutal):
        expected = re.compile(r'\\qtylist\[forbid-literal-units=false\]{1;7;2e\+30}{\\kilo\\gram}')
        computed = rf'{QuantityList(mass1, mass2, mass_brutal)}'
        assert expected.match(computed), \
            f"Expected {expected}, computed {computed}"

    def test_lengths(self, length1, length2):
        expected = re.compile(r'\\qtylist{2;3.2}{\\met(er|re)}')
        computed = rf'{QuantityList(length1, length2)}'
        assert expected.match(computed), \
            f"Expected {expected}, computed {computed}"

    def test_incommensurate(self, length1, mass2):
        with pytest.raises(pint.errors.DimensionalityError):
            _ = QuantityList(length1, mass2)


class TestProduct:
    def test_masses(self, mass1, mass2, mass_mega):
        expected = r'\qtyproduct{1 x 7 x 96.7}{\kilo\gram}'
        computed = rf'{QuantityProduct(mass1, mass2, mass_mega)}'
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"

    def test_masses_sun(self, mass1, mass2, mass_brutal):
        expected = re.compile(r'\\qtyproduct\[forbid-literal-units=false\]{1 x 7 x 2e\+30}{\\kilo\\gram}')
        computed = rf'{QuantityProduct(mass1, mass2, mass_brutal)}'
        assert expected.match(computed), \
            f"Expected {expected}, computed {computed}"

    def test_lengths(self, length1, length2):
        expected = re.compile(r'\\qtyproduct{2 x 3.2}{\\met(er|re)}')
        computed = rf'{QuantityProduct(length1, length2)}'
        assert expected.match(computed), \
            f"Expected {expected}, computed {computed}"

    def test_incommensurate(self, length1, mass2):
        with pytest.raises(pint.errors.DimensionalityError):
            _ = QuantityProduct(length1, mass2)


# --- Metadata propagation ------------------------------------------------
#
# Physical reasoning: a "symbol" names a specific quantity and does not
# compose under arithmetic (c - 1000 km/s is not c). Same for si_extra:
# formatting directives attached to one quantity should not silently propagate
# to a derived one. Operations that yield the *same* quantity in a different
# form (unit conversion, simplification, rounding) do preserve metadata.


class TestMetadataPreserved:
    """Operations that yield the same quantity must keep symbol and si_extra."""

    @pytest.fixture
    def labelled(self):
        return PhysicsQuantity.construct(
            5000, 'gram', symbol='m', si_extra={'round-mode': 'figures'},
        )

    def test_to_preserves(self, labelled):
        converted = labelled.to('kg')
        assert converted.symbol == 'm'
        assert converted.si_extra == {'round-mode': 'figures'}

    def test_simplify_preserves(self, labelled):
        simplified = labelled.simplify()
        assert simplified.symbol == 'm'
        assert simplified.si_extra == {'round-mode': 'figures'}

    def test_approximate_preserves(self, labelled):
        approx = labelled.approximate(2)
        assert approx.symbol == 'm'
        assert approx.si_extra == {'round-mode': 'figures'}


class TestMetadataDropped:
    """Operations that yield a *new* quantity must drop symbol and si_extra."""

    @pytest.fixture
    def labelled(self):
        return PhysicsQuantity.construct(
            5, 'kg', symbol='m', si_extra={'round-mode': 'figures'},
        )

    @pytest.fixture
    def other(self):
        return PhysicsQuantity.construct(3, 'kg', symbol='n')

    def test_add_drops(self, labelled, other):
        result = labelled + other
        assert result.symbol is None
        assert result.si_extra == {}

    def test_sub_drops(self, labelled, other):
        result = labelled - other
        assert result.symbol is None
        assert result.si_extra == {}

    def test_mul_drops(self, labelled, other):
        result = labelled * other
        assert result.symbol is None
        assert result.si_extra == {}

    def test_truediv_drops(self, labelled, other):
        result = labelled / other
        assert result.symbol is None
        assert result.si_extra == {}

    def test_neg_drops(self, labelled):
        result = -labelled
        assert result.symbol is None
        assert result.si_extra == {}

    def test_abs_drops(self, labelled):
        result = abs(labelled)
        assert result.symbol is None
        assert result.si_extra == {}

    def test_pow_drops(self, labelled):
        result = labelled ** 2
        assert result.symbol is None
        assert result.si_extra == {}

    def test_scalar_mul_drops(self, labelled):
        """Multiplying by a plain number is still a new quantity."""
        result = labelled * 2
        assert result.symbol is None
        assert result.si_extra == {}

    def test_sin_drops(self):
        import numpy as np
        angle = PhysicsQuantity.construct(
            np.pi / 2, 'radian', symbol=r'\theta',
            si_extra={'round-mode': 'figures'},
            )
        result = angle.sin()
        assert result.symbol is None
        assert result.si_extra == {}

    def test_log_drops(self):
        q = PhysicsQuantity.construct(
            2.718, '', symbol='x', si_extra={'round-mode': 'figures'},
        )
        result = q.log()
        assert result.symbol is None
        assert result.si_extra == {}

    def test_degrees_drops(self):
        import numpy as np
        angle = PhysicsQuantity.construct(
            np.pi, 'radian', symbol='a', si_extra={'round-mode': 'figures'},
        )
        result = angle.degrees()
        assert result.symbol is None
        assert result.si_extra == {}


# --- Pint interop --------------------------------------------------------


class TestPintInterop:
    """Binary ops with bare pint.Quantity operands must stay in the PhysicsQuantity world."""

    def test_mul_with_pint_quantity(self):
        from pint import UnitRegistry as u
        m = PhysicsQuantity.construct(5, 'kg')
        v = u.Quantity(2, 'meter / second')
        result = m * v
        assert isinstance(result, PhysicsQuantity), (
            f"expected PhysicsQuantity, got {type(result).__name__}"
        )

    def test_truediv_with_pint_quantity(self):
        from pint import UnitRegistry as u
        m = PhysicsQuantity.construct(5, 'kg')
        v = u.Quantity(2, 'meter / second')
        result = m / v
        assert isinstance(result, PhysicsQuantity)

    def test_add_with_plain_number_errors(self):
        """5 kg + 3 is a dimensionality error, not a silent pass-through."""
        m = PhysicsQuantity.construct(5, 'kg')
        with pytest.raises(pint.errors.DimensionalityError):
            _ = m + 3


# --- Approximate rounding ------------------------------------------------


class TestApproximate:
    """Sanity checks on `approximate()` rounding."""

    def test_positive_digits_required(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        with pytest.raises(AssertionError):
            m.approximate(0)

    def test_negative_digits_rejected(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        with pytest.raises(AssertionError):
            m.approximate(-1)

    def test_non_integer_digits_rejected(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        with pytest.raises(AssertionError):
            m.approximate(2.5)

    def test_symmetric_around_zero(self):
        """Positive and negative magnitudes must round symmetrically."""
        pos = PhysicsQuantity.construct(1.55, 'kg').approximate(2).mag
        neg = PhysicsQuantity.construct(-1.55, 'kg').approximate(2).mag
        assert pos == -neg, f"asymmetric rounding: {pos} vs {neg}"

    def test_zero_magnitude(self):
        m = PhysicsQuantity.construct(0.0, 'kg')
        assert m.approximate(3).mag == 0.0

    def test_significant_figures_one(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        assert m.approximate(1).mag == 100.0

    def test_significant_figures_three(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        assert m.approximate(3).mag == 123.0


# --- PhysicsQuantity.mag -------------------------------------------------


class TestOnlyUnit:
    """
    `only_unit()` returns the unit of a quantity formatted as a siunitx
    `\\unit{...}` command, without the magnitude.  The output can be used
    in templates where you want to print the unit separately from the value.
    """

    def test_kilogram(self):
        assert PhysicsQuantity.construct(5, 'kg').only_unit() == r'\unit{\kilo\gram}'

    def test_meter_per_second_squared(self):
        assert PhysicsQuantity.construct(9.8, 'meter/second^2').only_unit() == \
               r'\unit{\metre\per\second\squared}'

    def test_meter_per_second(self):
        assert PhysicsQuantity.construct(10, 'meter/second').only_unit() == \
               r'\unit{\metre\per\second}'

    def test_celsius(self):
        """Degree-Celsius is converted to siunitx \\celsius."""
        from pint import UnitRegistry as u
        T = PhysicsQuantity(u.Quantity(25, 'degree_Celsius'))
        assert T.only_unit() == r'\unit{\celsius}'

    def test_joule(self):
        assert PhysicsQuantity.construct(1.5, 'joule').only_unit() == r'\unit{\joule}'

    def test_pascal(self):
        assert PhysicsQuantity.construct(101325, 'Pa').only_unit() == r'\unit{\pascal}'

    def test_dimensionless_gives_unit_one(self):
        """A dimensionless quantity produces \\unit{1}."""
        d = PhysicsQuantity.construct(3.14, '')
        assert d.only_unit() == r'\unit{1}'

    def test_si_extra_included(self):
        """si_extra options appear between \\unit and the braces."""
        m = PhysicsQuantity.construct(5, 'kg', si_extra={'round-mode': 'figures'})
        assert m.only_unit() == r'\unit[round-mode=figures]{\kilo\gram}'

    def test_symbol_ignored(self):
        """The symbol is a display label for the quantity, not part of its unit."""
        m = PhysicsQuantity.construct(5, 'meter', symbol='d')
        assert m.only_unit() == r'\unit{\metre}'

    def test_after_unit_conversion(self):
        """Unit reflects the converted unit, not the original."""
        g = PhysicsQuantity.construct(1000, 'gram').to('kilogram')
        assert g.only_unit() == r'\unit{\kilo\gram}'

    def test_magnitude_does_not_appear(self):
        """Sanity check: the output contains no numeric characters."""
        m = PhysicsQuantity.construct(12345.678, 'kg')
        result = m.only_unit()
        assert not any(c.isdigit() for c in result), \
            f"Magnitude appeared in unit output: {result!r}"

    def test_starts_with_unit_command(self):
        m = PhysicsQuantity.construct(5, 'kg')
        assert m.only_unit().startswith(r'\unit')

    def test_jinja_filter(self):
        """The `| unit` Jinja filter wires correctly to only_unit()."""
        from core.builder.jinja import MarkdownJinjaRenderer
        renderer = MarkdownJinjaRenderer()
        ctx = {'q': PhysicsQuantity.construct(9.8, 'meter/second^2')}
        result = renderer.render('(§ q | unit §)', ctx)
        assert result == r'\unit{\metre\per\second\squared}'


class TestMag:
    """
    `mag` is a thin accessor for the underlying pint magnitude. It returns
    whatever numeric type pint stores (int, float, or numpy scalar after
    operations like np.floor/np.ceil).
    """

    def test_int_construction(self):
        assert PhysicsQuantity.construct(7, 'kg').mag == 7

    def test_float_construction(self):
        assert PhysicsQuantity.construct(5.5, 'kg').mag == pytest.approx(5.5)

    def test_negative(self):
        assert PhysicsQuantity.construct(-3.7, 'kg').mag == pytest.approx(-3.7)

    def test_dimensionless(self):
        assert PhysicsQuantity.construct(2.5, '').mag == pytest.approx(2.5)

    def test_after_unit_conversion(self):
        """`to()` may change int -> float as a side effect of conversion."""
        kg = PhysicsQuantity.construct(1, 'kilogram')
        assert kg.to('gram').mag == pytest.approx(1000)

    def test_mag_does_not_carry_units(self):
        """The bare magnitude is a number, not a pint Quantity."""
        m = PhysicsQuantity.construct(5, 'kg')
        assert not hasattr(m.mag, 'units')


# --- PhysicsQuantity.floor / .ceil --------------------------------------


class TestFloorCeil:
    """
    `floor` and `ceil` round the magnitude toward -inf and +inf respectively,
    keeping the unit. They return a new PhysicsQuantity; metadata is dropped
    because the result is a different quantity from the input.
    """

    def test_floor_positive(self):
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert m.floor().mag == pytest.approx(5)

    def test_ceil_positive(self):
        m = PhysicsQuantity.construct(5.3, 'kg')
        assert m.ceil().mag == pytest.approx(6)

    def test_floor_negative_rounds_toward_neg_inf(self):
        """floor(-2.3) is -3, not -2 (toward -inf, not toward zero)."""
        m = PhysicsQuantity.construct(-2.3, 'meter')
        assert m.floor().mag == pytest.approx(-3)

    def test_ceil_negative_rounds_toward_pos_inf(self):
        """ceil(-2.3) is -2, not -3 (toward +inf, not toward zero)."""
        m = PhysicsQuantity.construct(-2.3, 'meter')
        assert m.ceil().mag == pytest.approx(-2)

    def test_floor_of_integer(self):
        m = PhysicsQuantity.construct(5.0, 'kg')
        assert m.floor().mag == pytest.approx(5)

    def test_ceil_of_integer(self):
        m = PhysicsQuantity.construct(5.0, 'kg')
        assert m.ceil().mag == pytest.approx(5)

    def test_floor_of_zero(self):
        m = PhysicsQuantity.construct(0, 'kg')
        assert m.floor().mag == pytest.approx(0)

    def test_round_goes_to_the_nearer_side(self):
        assert PhysicsQuantity.construct(5.7, 'kg').round().mag == pytest.approx(6)
        assert PhysicsQuantity.construct(5.3, 'kg').round().mag == pytest.approx(5)

    def test_round_negative(self):
        """Toward the nearer whole number either way, unlike floor and ceil."""
        assert PhysicsQuantity.construct(-2.3, 'meter').round().mag == pytest.approx(-2)
        assert PhysicsQuantity.construct(-2.7, 'meter').round().mag == pytest.approx(-3)

    def test_round_keeps_the_unit(self):
        assert PhysicsQuantity.construct(5.7, 'kg').round() == PhysicsQuantity.construct(6, 'kg')

    def test_round_halves_go_to_even(self):
        """numpy's rule, and Python's: 2.5 rounds to 2, not 3."""
        assert PhysicsQuantity.construct(2.5, 'kg').round().mag == pytest.approx(2)
        assert PhysicsQuantity.construct(3.5, 'kg').round().mag == pytest.approx(4)

    def test_ceil_of_zero(self):
        m = PhysicsQuantity.construct(0, 'kg')
        assert m.ceil().mag == pytest.approx(0)

    def test_floor_preserves_unit(self):
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert m.floor().unit == m.unit

    def test_ceil_preserves_unit(self):
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert m.ceil().unit == m.unit

    def test_floor_returns_physics_quantity(self):
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert isinstance(m.floor(), PhysicsQuantity)

    def test_ceil_returns_physics_quantity(self):
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert isinstance(m.ceil(), PhysicsQuantity)

    def test_floor_drops_symbol(self):
        """floor produces a new quantity, so the original symbol does not carry over."""
        m = PhysicsQuantity.construct(5.7, 'kg', symbol='m')
        assert m.floor().symbol is None

    def test_floor_drops_si_extra(self):
        m = PhysicsQuantity.construct(5.7, 'kg', si_extra={'round-mode': 'figures'})
        assert m.floor().si_extra == {}

    def test_ceil_drops_symbol(self):
        m = PhysicsQuantity.construct(5.7, 'kg', symbol='m')
        assert m.ceil().symbol is None

    def test_ceil_drops_si_extra(self):
        m = PhysicsQuantity.construct(5.7, 'kg', si_extra={'round-mode': 'figures'})
        assert m.ceil().si_extra == {}

    def test_floor_dimensionless_renders_with_num(self):
        """Dimensionless results should still use \\num, not \\qty."""
        d = PhysicsQuantity.construct(2.7, '')
        assert str(d.floor()).startswith(r'\num{')

    def test_floor_then_ceil_idempotent_on_floored_value(self):
        """ceil of a floored integer is the same value."""
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert m.floor().ceil().mag == pytest.approx(5)


# --- PhysicsQuantity.widen -----------------------------------------------


class TestQuantityWiden:
    """
    PhysicsQuantity.widen(v) constructs an asymmetric tolerance range
    [(1-v)*x, (1+v)*x] from a single value, with min/max ordered correctly
    regardless of sign.
    """

    def test_positive_value(self):
        m = PhysicsQuantity.construct(100, 'meter')
        r = m.widen(0.05)
        assert r.minimum.mag == pytest.approx(95)
        assert r.maximum.mag == pytest.approx(105)

    def test_negative_value(self):
        """For x < 0, the result is still ordered (min < max)."""
        m = PhysicsQuantity.construct(-100, 'meter')
        r = m.widen(0.05)
        assert r.minimum.mag == pytest.approx(-105)
        assert r.maximum.mag == pytest.approx(-95)

    def test_large_factor_crosses_zero(self):
        """value >= 1 produces a range crossing zero."""
        m = PhysicsQuantity.construct(100, 'meter')
        r = m.widen(1.5)
        assert r.minimum.mag == pytest.approx(-50)
        assert r.maximum.mag == pytest.approx(250)

    def test_zero_value(self):
        """widen on x == 0 gives a degenerate range at zero."""
        m = PhysicsQuantity.construct(0, 'meter')
        r = m.widen(0.1)
        assert r.minimum.mag == 0
        assert r.maximum.mag == 0

    def test_zero_factor(self):
        """widen(0) gives a degenerate range at the original value."""
        m = PhysicsQuantity.construct(42, 'meter')
        r = m.widen(0)
        assert r.minimum.mag == pytest.approx(42)
        assert r.maximum.mag == pytest.approx(42)

    def test_negative_factor_rejected(self):
        m = PhysicsQuantity.construct(100, 'meter')
        with pytest.raises(AssertionError, match="non-negative"):
            m.widen(-0.05)

    def test_unit_preserved(self):
        m = PhysicsQuantity.construct(100, 'meter')
        r = m.widen(0.1)
        assert r.minimum.unit == r.maximum.unit
        assert str(r.minimum.unit) == 'meter'

    def test_returns_quantity_range(self):
        m = PhysicsQuantity.construct(5, 'kg')
        assert isinstance(m.widen(0.1), QuantityRange)


# --- Range guardrails ----------------------------------------------------


class TestRangeGuardrails:
    """Ranges with invalid bounds should be rejected at construction."""

    @pytest.fixture
    def m1(self):
        return PhysicsQuantity.construct(1, 'kg')

    @pytest.fixture
    def m3(self):
        return PhysicsQuantity.construct(3, 'kg')

    def test_swapped_endpoints_rejected(self, m1, m3):
        with pytest.raises(ValueError, match="must not exceed"):
            QuantityRange(m3, m1)

    def test_widen_positive_range(self, m1, m3):
        """[1, 3] widened by 0.1: width grows from 2 to 2.2, symmetric around centre 2."""
        r = QuantityRange(m1, m3).widen(0.1)
        assert r.minimum.mag == pytest.approx(0.9)
        assert r.maximum.mag == pytest.approx(3.1)

    def test_widen_negative_range(self):
        """A negative-valued range must widen, not narrow."""
        a = PhysicsQuantity.construct(-3, 'kg')
        b = PhysicsQuantity.construct(-1, 'kg')
        r = QuantityRange(a, b).widen(0.1)
        assert r.minimum.mag == pytest.approx(-3.1)
        assert r.maximum.mag == pytest.approx(-0.9)

    def test_widen_zero_centred_range(self):
        """Range straddling zero widens symmetrically."""
        a = PhysicsQuantity.construct(-1, 'kg')
        b = PhysicsQuantity.construct(1, 'kg')
        r = QuantityRange(a, b).widen(0.5)
        assert r.minimum.mag == pytest.approx(-1.5)
        assert r.maximum.mag == pytest.approx(1.5)

    def test_widen_large_factor_allowed(self, m1, m3):
        """value >= 1 is now permitted; the range simply grows substantially."""
        r = QuantityRange(m1, m3).widen(1.5)
        # Centre 2, half-width 1, scaled by 2.5 -> half-width 2.5
        assert r.minimum.mag == pytest.approx(-0.5)
        assert r.maximum.mag == pytest.approx(4.5)

    def test_widen_negative_value_rejected(self, m1, m3):
        """widen(-0.1) would contract; reject so 'widen' stays honest about its name."""
        with pytest.raises(AssertionError, match="non-negative"):
            QuantityRange(m1, m3).widen(-0.1)

    def test_widen_identity(self, m1, m3):
        """widen(0) returns an equivalent range."""
        r = QuantityRange(m1, m3).widen(0)
        assert r.minimum.mag == pytest.approx(1)
        assert r.maximum.mag == pytest.approx(3)

    def test_widen_degenerate_range(self):
        """A range with min==max stays degenerate; half-width is zero."""
        a = PhysicsQuantity.construct(5, 'kg')
        r = QuantityRange(a, a).widen(0.1)
        assert r.minimum.mag == pytest.approx(5)
        assert r.maximum.mag == pytest.approx(5)


# --- si_extra clash detection --------------------------------------------


class TestSiExtraClash:
    """
    When two quantities with conflicting si_extra keys are combined into a
    QuantityRange or QuantityList, the conflict should be surfaced rather
    than silently resolved.
    """

    @pytest.fixture
    def m_figures(self):
        return PhysicsQuantity.construct(1, 'kg', si_extra={'round-mode': 'figures'})

    @pytest.fixture
    def m_places(self):
        return PhysicsQuantity.construct(2, 'kg', si_extra={'round-mode': 'places'})

    @pytest.fixture
    def m_plain(self):
        return PhysicsQuantity.construct(3, 'kg')

    def test_range_compatible_keys_merge(self, m_figures, m_plain):
        """Non-conflicting si_extra should merge cleanly."""
        r = QuantityRange(m_figures, m_plain)
        assert r.si_extra == {'round-mode': 'figures'}

    def test_list_compatible_keys_merge(self, m_figures, m_plain):
        ql = QuantityList(m_figures, m_plain)
        assert ql.si_extra == {'round-mode': 'figures'}

    def test_range_conflicting_keys_raises(self, m_figures, m_places):
        with pytest.raises(ValueError, match="round-mode"):
            QuantityRange(m_figures, m_places)

    def test_list_conflicting_keys_raises(self, m_figures, m_places):
        with pytest.raises(ValueError, match="round-mode"):
            QuantityList(m_figures, m_places)

    def test_product_compatible_keys_merge(self, m_figures, m_plain):
        qp = QuantityProduct(m_figures, m_plain)
        assert qp.si_extra == {'round-mode': 'figures'}

    def test_product_conflicting_keys_raises(self, m_figures, m_places):
        with pytest.raises(ValueError, match="round-mode"):
            QuantityProduct(m_figures, m_places)


# --- QuantityList edge cases ---------------------------------------------


class TestQuantityListEdgeCases:
    def test_empty_rejected(self):
        with pytest.raises(AssertionError):
            QuantityList()

    def test_single_element(self):
        m = PhysicsQuantity.construct(5, 'kg')
        assert rf'{QuantityList(m)}' == r'\qtylist{5}{\kilo\gram}'

    def test_unit_of_first_wins(self):
        """
        QuantityList coerces all elements to the first element's unit.
        Note: pint's conversion may change int→float, so '1' becomes '1.0'
        when it is the result of a conversion rather than a literal.
        """
        g = PhysicsQuantity.construct(1000, 'gram')
        kg = PhysicsQuantity.construct(1, 'kilogram')
        assert rf'{QuantityList(g, kg)}' == r'\qtylist{1000;1000.0}{\gram}'
        assert rf'{QuantityList(kg, g)}' == r'\qtylist{1;1.0}{\kilo\gram}'


class TestQuantityProductEdgeCases:
    def test_empty_rejected(self):
        with pytest.raises(AssertionError):
            QuantityProduct()

    def test_single_element(self):
        m = PhysicsQuantity.construct(5, 'kg')
        assert rf'{QuantityProduct(m)}' == r'\qtyproduct{5}{\kilo\gram}'

    def test_unit_of_first_wins(self):
        """
        QuantityProduct coerces all elements to the first element's unit.
        Note: pint's conversion may change int→float, so '1' becomes '1.0'
        when it is the result of a conversion rather than a literal.
        """
        g = PhysicsQuantity.construct(1000, 'gram')
        kg = PhysicsQuantity.construct(1, 'kilogram')
        assert rf'{QuantityProduct(g, kg)}' == r'\qtyproduct{1000 x 1000.0}{\gram}'
        assert rf'{QuantityProduct(kg, g)}' == r'\qtyproduct{1 x 1.0}{\kilo\gram}'


class TestQuantityListCollectionParity:
    """
    QuantityList should behave like a first-class sequence of its
    (unit-coerced) elements, matching len()/iteration/indexing users would
    expect from any collection type.
    """

    def test_len(self, mass1, mass2, mass_mega):
        assert len(QuantityList(mass1, mass2, mass_mega)) == 3

    def test_iter(self, mass1, mass2):
        ql = QuantityList(mass1, mass2)
        assert list(ql) == [mass1, mass2]

    def test_getitem(self, mass1, mass2, mass_mega):
        ql = QuantityList(mass1, mass2, mass_mega)
        assert ql[0] == mass1
        assert ql[-1] == mass_mega

    def test_repr(self, mass1, mass2):
        assert repr(QuantityList(mass1, mass2)) == f"QuantityList ({[mass1, mass2]})"

    def test_eq(self, mass1, mass2):
        assert QuantityList(mass1, mass2) == QuantityList(mass1, mass2)

    def test_eq_different_elements(self, mass1, mass2, mass_mega):
        assert QuantityList(mass1, mass2) != QuantityList(mass1, mass_mega)

    def test_eq_unit_coercion(self):
        """Equality compares coerced elements, so equivalent quantities in
        different literal units still compare equal."""
        g = PhysicsQuantity.construct(1000, 'gram')
        kg = PhysicsQuantity.construct(1, 'kilogram')
        assert QuantityList(kg, g) == QuantityList(kg, g)

    def test_eq_not_implemented_for_other_types(self, mass1, mass2):
        assert QuantityList(mass1, mass2).__eq__(mass1) is NotImplemented


class TestQuantityProductCollectionParity:
    """
    QuantityProduct should behave like a first-class sequence of its
    (unit-coerced) elements, matching len()/iteration/indexing users would
    expect from any collection type.
    """

    def test_len(self, mass1, mass2, mass_mega):
        assert len(QuantityProduct(mass1, mass2, mass_mega)) == 3

    def test_iter(self, mass1, mass2):
        qp = QuantityProduct(mass1, mass2)
        assert list(qp) == [mass1, mass2]

    def test_getitem(self, mass1, mass2, mass_mega):
        qp = QuantityProduct(mass1, mass2, mass_mega)
        assert qp[0] == mass1
        assert qp[-1] == mass_mega

    def test_repr(self, mass1, mass2):
        assert repr(QuantityProduct(mass1, mass2)) == f"QuantityProduct ({[mass1, mass2]})"

    def test_eq(self, mass1, mass2):
        assert QuantityProduct(mass1, mass2) == QuantityProduct(mass1, mass2)

    def test_eq_different_elements(self, mass1, mass2, mass_mega):
        assert QuantityProduct(mass1, mass2) != QuantityProduct(mass1, mass_mega)

    def test_eq_unit_coercion(self):
        """Equality compares coerced elements, so equivalent quantities in
        different literal units still compare equal."""
        g = PhysicsQuantity.construct(1000, 'gram')
        kg = PhysicsQuantity.construct(1, 'kilogram')
        assert QuantityProduct(kg, g) == QuantityProduct(kg, g)

    def test_eq_not_implemented_for_other_types(self, mass1, mass2):
        assert QuantityProduct(mass1, mass2).__eq__(mass1) is NotImplemented


# --- Formatting ----------------------------------------------------------


class TestFormatting:
    def test_dimensionless_uses_num(self):
        d = PhysicsQuantity.construct(3.14, '')
        assert str(d).startswith(r'\num{')

    def test_dimensionless_has_no_trailing_braces(self):
        """\num{3.14} is the correct form; \num{3.14}{} has a stray empty group."""
        d = PhysicsQuantity.construct(3.14, '')
        assert str(d) == r'\num{3.14}'

    def test_dimensionless_range_uses_numrange(self):
        a = PhysicsQuantity.construct(0.1, '')
        b = PhysicsQuantity.construct(0.5, '')
        assert rf'{QuantityRange(a, b)}' == r'\numrange{0.1}{0.5}'

    def test_dimensionless_list_uses_numlist(self):
        a = PhysicsQuantity.construct(0.1, '')
        b = PhysicsQuantity.construct(0.5, '')
        assert rf'{QuantityList(a, b)}' == r'\numlist{0.1;0.5}'

    def test_dimensionless_product_uses_numproduct(self):
        a = PhysicsQuantity.construct(0.1, '')
        b = PhysicsQuantity.construct(0.5, '')
        assert rf'{QuantityProduct(a, b)}' == r'\numproduct{0.1 x 0.5}'

    def test_with_unit_uses_qty(self):
        m = PhysicsQuantity.construct(5, 'kg')
        assert str(m).startswith(r'\qty{')

    def test_si_extra_appears_in_output(self):
        m = PhysicsQuantity.construct(
            5, 'kg', si_extra={'round-mode': 'figures'},
        )
        assert 'round-mode=figures' in str(m)


# --- equals_*/approx_* string formatting ---------------------------------


class TestEqualsApprox:
    """`equals_*` use ` = `; `approx_*` use `\\approx` and otherwise format identically."""

    def test_equals_float(self, mass_mega):
        assert mass_mega.equals_float(2) == r'm_D = \qty{96.70}{\kilo\gram}'

    def test_equals_general(self, mass_mega):
        assert mass_mega.equals_general(2) == r'm_D = \qty{97}{\kilo\gram}'

    def test_approx_float(self, mass_mega):
        assert mass_mega.approx_float(2) == r'm_D \approx \qty{96.70}{\kilo\gram}'

    def test_approx_general(self, mass_mega):
        assert mass_mega.approx_general(2) == r'm_D \approx \qty{97}{\kilo\gram}'

    def test_equals_exponential(self, mass_mega):
        assert mass_mega.equals_exponential(2) == r'm_D = \qty{9.67e+01}{\kilo\gram}'

    def test_approx_exponential(self, mass_mega):
        assert mass_mega.approx_exponential(2) == r'm_D \approx \qty{9.67e+01}{\kilo\gram}'

    def test_approx_float_precision_zero(self, mass_mega):
        assert mass_mega.approx_float(0) == r'm_D \approx \qty{97}{\kilo\gram}'

    def test_approx_matches_equals_except_operator(self, mass_mega):
        """`approx_*` should format identically to `equals_*` other than `=` vs `\\approx`."""
        assert mass_mega.approx_float(3).replace(r'\approx', '=') == mass_mega.equals_float(3)
        assert mass_mega.approx_general(3).replace(r'\approx', '=') == mass_mega.equals_general(3)
        assert mass_mega.approx_exponential(3).replace(r'\approx', '=') == mass_mega.equals_exponential(3)

    def test_precision_is_optional(self, mass_mega):
        """Omitting precision falls back to the bare 'f'/'g' spec, as in `format_float`."""
        assert mass_mega.approx_float() == r'm_D \approx \qty{96.700000}{\kilo\gram}'
        assert mass_mega.approx_general() == r'm_D \approx \qty{96.7}{\kilo\gram}'
        assert mass_mega.equals_float() == r'm_D = \qty{96.700000}{\kilo\gram}'
        assert mass_mega.equals_general() == r'm_D = \qty{96.7}{\kilo\gram}'
        assert mass_mega.equals_exponential() == r'm_D = \qty{9.670000e+01}{\kilo\gram}'

    def test_explicit_none_precision_matches_omitted(self, mass_mega):
        """`None` is the documented way to say "no precision", not an error."""
        assert mass_mega.approx_float(None) == mass_mega.approx_float()
        assert mass_mega.equals_general(None) == mass_mega.equals_general()


class TestEqualsApproxWithoutSymbol:
    """
    Rendering a symbol-less quantity with a symbol form must crash, not silently
    print `None = \\qty{...}` into the text.
    """

    @pytest.fixture
    def anonymous(self):
        return PhysicsQuantity.construct(11.345, 'm/s^2')

    @pytest.mark.parametrize('method', ['equals_float', 'equals_general', 'equals_exponential',
                                        'approx_float', 'approx_general', 'approx_exponential'])
    def test_raises_without_symbol(self, anonymous, method):
        with pytest.raises(MissingSymbolError):
            getattr(anonymous, method)(2)

    @pytest.mark.parametrize('method', ['equals_float', 'equals_general', 'equals_exponential',
                                        'approx_float', 'approx_general', 'approx_exponential'])
    def test_raises_without_symbol_no_precision(self, anonymous, method):
        with pytest.raises(MissingSymbolError):
            getattr(anonymous, method)()

    @pytest.mark.parametrize('prop', ['equals', 'eq'])
    def test_equals_property_raises_without_symbol(self, anonymous, prop):
        with pytest.raises(MissingSymbolError):
            getattr(anonymous, prop)

    def test_error_names_the_method(self, anonymous):
        with pytest.raises(MissingSymbolError, match='equals_float'):
            anonymous.equals_float(2)

    def test_symbol_less_formatting_still_works(self, anonymous):
        """Only the symbol forms are affected; plain formatting is untouched."""
        assert anonymous.full == r'\qty{11.345}{\metre\per\second\squared}'
        assert f'{anonymous:.1f}' == r'\qty{11.3}{\metre\per\second\squared}'

    def test_aliasing_fixes_it(self, anonymous):
        assert anonymous.alias('a').equals_float(2) == r'a = \qty{11.35}{\metre\per\second\squared}'

    def test_symbol_set_to_none_again_raises(self, mass_mega):
        """The symbol is the one mutable field -- clearing it must re-arm the check."""
        mass_mega.symbol = None
        with pytest.raises(MissingSymbolError):
            mass_mega.equals_float(2)


# --- Equality semantics --------------------------------------------------


class TestEquality:
    """Equality compares physical values only; metadata is ignored by design."""

    def test_same_value_different_symbol(self):
        a = PhysicsQuantity.construct(5, 'kg', symbol='X')
        b = PhysicsQuantity.construct(5, 'kg', symbol='Y')
        assert a == b

    def test_same_value_different_si_extra(self):
        a = PhysicsQuantity.construct(5, 'kg', si_extra={'round-mode': 'figures'})
        b = PhysicsQuantity.construct(5, 'kg')
        assert a == b

    def test_same_value_different_units(self):
        """pint's equality handles unit conversion under the hood."""
        a = PhysicsQuantity.construct(1, 'kilogram')
        b = PhysicsQuantity.construct(1000, 'gram')
        assert a == b

    def test_different_values_not_equal(self):
        a = PhysicsQuantity.construct(5, 'kg')
        b = PhysicsQuantity.construct(7, 'kg')
        assert a != b

    def test_not_equal_to_non_quantity(self):
        """Comparison with non-PhysicsQuantity returns False, does not crash."""
        m = PhysicsQuantity.construct(5, 'kg')
        assert (m == 5) is False
        assert (m == "5 kg") is False
        assert (m == None) is False

    def test_unhashable(self):
        """Defining __eq__ without __hash__ makes instances unhashable."""
        m = PhysicsQuantity.construct(5, 'kg')
        with pytest.raises(TypeError):
            hash(m)


class TestAbs:
    """
    `abs` keeps the unit and drops the sign, like `floor` and `ceil` keep the unit and round.

    It exists so `|abs` works in a `derived:` expression: a result that is the magnitude of a
    difference had no way to say so, because Jinja's `abs` filter calls Python's `abs`, and
    without `__abs__` that is a `TypeError` on a quantity.
    """

    def test_negative_becomes_positive(self):
        assert abs(PhysicsQuantity.construct(-3, 'metre')).mag == pytest.approx(3)

    def test_positive_is_unchanged(self):
        assert abs(PhysicsQuantity.construct(3, 'metre')).mag == pytest.approx(3)

    def test_zero(self):
        assert abs(PhysicsQuantity.construct(0, 'metre')).mag == pytest.approx(0)

    def test_preserves_unit(self):
        m = PhysicsQuantity.construct(-5.7, 'kg')
        assert abs(m).unit == m.unit

    def test_returns_physics_quantity(self):
        assert isinstance(abs(PhysicsQuantity.construct(-1, 'kg')), PhysicsQuantity)

    def test_of_a_difference(self):
        """The case it is for: `\\Abs{\\FDiff{p}}`, a drop stated as a magnitude."""
        p1 = PhysicsQuantity.construct(0.7, 'megapascal')
        p2 = PhysicsQuantity.construct(10.5, 'megapascal')
        assert abs(p1 - p2).mag == pytest.approx(9.8)


class TestOrdering:
    """
    Quantities compare, so `|max`, `|min` and `sorted` work on them.

    Only equality existed before, which made a result like "the larger of the two branches"
    inexpressible in `derived:` -- Jinja's `max` filter sorts, and sorting needs `<`.
    """

    def test_less_than(self):
        assert PhysicsQuantity.construct(3, 'metre') < PhysicsQuantity.construct(5, 'metre')

    def test_greater_than(self):
        assert PhysicsQuantity.construct(5, 'metre') > PhysicsQuantity.construct(3, 'metre')

    def test_equal_values_are_neither_less_nor_greater(self):
        a, b = (PhysicsQuantity.construct(3, 'metre') for _ in range(2))
        assert not a < b and not a > b
        assert a <= b and a >= b

    def test_across_units_of_the_same_dimension(self):
        """pint converts, so 400 cm is more than 3 m rather than less."""
        assert PhysicsQuantity.construct(400, 'cm') > PhysicsQuantity.construct(3, 'metre')

    def test_max_picks_the_larger(self):
        quantities = [PhysicsQuantity.construct(3, 'metre'), PhysicsQuantity.construct(400, 'cm')]
        assert max(quantities).mag == pytest.approx(400)

    def test_sorted_orders_by_physical_value(self):
        given = [PhysicsQuantity.construct(5, 'metre'),
                 PhysicsQuantity.construct(50, 'cm'),
                 PhysicsQuantity.construct(3, 'metre')]
        assert [q.mag for q in sorted(given)] == [50, 3, 5]

    def test_incomparable_dimensions_raise(self):
        """
        Not `False`. A metre is not less than a second, nor more, and answering either would
        compare two magnitudes that mean nothing to each other.
        """
        with pytest.raises(pint.DimensionalityError):
            _ = PhysicsQuantity.construct(1, 'metre') < PhysicsQuantity.construct(1, 'second')

    def test_dimensionless_compares_with_a_plain_number(self):
        assert PhysicsQuantity.construct(3, '1') < 5

    def test_comparison_with_a_string_raises(self):
        """`__eq__` returns False for a non-quantity; ordering has no such answer to give."""
        with pytest.raises(TypeError):
            _ = PhysicsQuantity.construct(3, 'metre') < 'tall'


# --- PhysicsConstant -----------------------------------------------------


class TestPhysicsConstant:
    """Smoke tests for the PhysicsConstant subclass."""

    @pytest.fixture
    def g(self):
        from pint import UnitRegistry as u

        from core.builder.context.quantities.constant import PhysicsConstant
        return PhysicsConstant(
            'gforce', u.Quantity(9.80665, 'meter / second^2'), digits=2,
        )

    def test_full(self, g):
        assert r'\qty{' in g.full
        assert r'\metre' in g.full

    def test_approx(self, g):
        """g with 2 digits rounds to 9.8 m/s^2."""
        assert g.approx.mag == pytest.approx(9.8)

    def test_full_approx(self, g):
        """Previously crashed with `ValueError: Invalid format specifier`."""
        rendered = g.full_approx
        assert r'\qty{' in rendered
        assert '9.8' in rendered


# --- pint -> siunitx unit macros -----------------------------------------


class TestUnitMacros:
    r"""
    `pint`'s `Lx` format builds a macro from the unit's *full name*, so every
    multi-word unit arrives as invalid TeX (`\astronomical_unit`). Known ones are
    mapped onto the macros declared in `core/latex/siunitx.tex`; the rest must
    raise rather than reach XeLaTeX.
    """

    @pytest.mark.parametrize("unit,macro", [
        pytest.param('au', r'\au', id='astronomical_unit'),
        pytest.param('ly', r'\lightyear', id='light_year'),
        pytest.param('t', r'\tonne', id='metric_ton'),
        pytest.param('eV', r'\electronvolt', id='electron_volt'),
        pytest.param('degC', r'\celsius', id='degree_Celsius'),
        pytest.param('delta_degC', r'\dcelsius', id='delta_degree_Celsius'),
        pytest.param('degF', r'\fahrenheit', id='degree_Fahrenheit'),
        pytest.param('rpm', r'\rpm', id='revolutions_per_minute'),
        pytest.param('atm', r'\atmosphere', id='standard_atmosphere'),
        pytest.param('u', r'\atomicmass', id='unified_atomic_mass_unit'),
        pytest.param('px', r'\pixel', id='css_pixel'),
        pytest.param('g_0', r'\gforce', id='standard_gravity'),
        pytest.param('Wh', r'\watthour', id='watt_hour'),
    ])
    def test_mapped_units(self, unit, macro):
        q = PhysicsQuantity.construct(1.5, unit)
        assert f'{q:g}' == rf'\qty{{1.5}}{{{macro}}}'
        assert q.only_unit() == rf'\unit{{{macro}}}'

    def test_mapped_unit_inside_compound(self):
        """A mapped macro must survive being combined with prefixes and `\\per`."""
        assert PhysicsQuantity.construct(1, 'au/year').only_unit() == r'\unit{\au\per\year}'

    @pytest.mark.parametrize("unit", ['nautical_mile', 'psi', 'tropical_year', 'ft_lb', 'sidereal_day'])
    def test_unmapped_unit_raises(self, unit):
        with pytest.raises(UnknownUnitMacroError):
            f"{PhysicsQuantity.construct(1, unit):g}"

    def test_unmapped_unit_raises_from_only_unit_too(self):
        with pytest.raises(UnknownUnitMacroError):
            PhysicsQuantity.construct(1, 'nautical_mile').only_unit()

    def test_error_names_the_offending_unit(self):
        with pytest.raises(UnknownUnitMacroError, match='nautical_mile') as excinfo:
            f"{PhysicsQuantity.construct(1, 'nautical_mile'):g}"
        assert excinfo.value.name == 'nautical_mile'

    def test_compound_pint_alias_raises(self):
        """`mps` is one pint unit named `meter_per_second`, not `m/s` -- so it must raise."""
        with pytest.raises(UnknownUnitMacroError):
            f"{PhysicsQuantity.construct(1, 'mps'):g}"
        # ... while the same physical unit spelled out is fine
        assert PhysicsQuantity.construct(1, 'm/s').only_unit() == r'\unit{\metre\per\second}'

    @pytest.mark.parametrize("unit,macro", [
        pytest.param('kg', r'\kilo\gram', id='prefixed'),
        pytest.param('km/h', r'\kilo\metre\per\hour', id='per'),
        pytest.param('kg/m^3', r'\kilo\gram\per\metre\cubed', id='power'),
        pytest.param('J', r'\joule', id='named'),
    ])
    def test_ordinary_units_untouched(self, unit, macro):
        assert PhysicsQuantity.construct(1, unit).only_unit() == rf'\unit{{{macro}}}'


class TestBritishSpelling:
    r"""
    pint names two SI units the American way. siunitx declares both spellings and they typeset
    identically, so this is about the rendered *source*, which the repository writes in British
    English throughout -- and which used to come out mixed, sometimes within one sentence, once a
    hand-written `\qty{4}{\milli\litre}` sat beside the same quantity taken from `values:`.
    """

    @pytest.mark.parametrize("unit,macro", [
        pytest.param('metre', r'\metre', id='metre-in'),
        pytest.param('meter', r'\metre', id='meter-in'),
        pytest.param('litre', r'\litre', id='litre-in'),
        pytest.param('liter', r'\litre', id='liter-in'),
    ])
    def test_either_spelling_renders_british(self, unit, macro):
        """Whichever the source writes -- and pint accepts both -- one spelling comes out."""
        assert PhysicsQuantity.construct(1, unit).only_unit() == rf'\unit{{{macro}}}'

    @pytest.mark.parametrize("unit,macro", [
        pytest.param('cm', r'\centi\metre', id='prefix'),
        pytest.param('ml', r'\milli\litre', id='prefix-litre'),
        pytest.param('kg/m^3', r'\kilo\gram\per\metre\cubed', id='compound'),
        pytest.param('m/s^2', r'\metre\per\second\squared', id='power'),
    ])
    def test_through_prefixes_and_compounds(self, unit, macro):
        assert PhysicsQuantity.construct(1, unit).only_unit() == rf'\unit{{{macro}}}'

    def test_other_units_are_left_alone(self):
        """
        Two names and no others. Unlike `PINT_TO_SIUNITX`, which raises for anything it does not
        know, an unlisted spelling here is simply not its business.
        """
        assert PhysicsQuantity.construct(1, 'gram').only_unit() == r'\unit{\gram}'
        assert PhysicsQuantity.construct(1, 'second').only_unit() == r'\unit{\second}'

    def test_whole_names_only(self):
        r"""
        A `str.replace` of `\meter` would also rewrite the head of a longer name that happens to
        start the same way; `\minute` and `\metric_ton` are the neighbours in reach today.
        """
        assert PhysicsQuantity.construct(1, 'minute').only_unit() == r'\unit{\minute}'
        assert PhysicsQuantity.construct(1, 't').only_unit() == r'\unit{\tonne}'
