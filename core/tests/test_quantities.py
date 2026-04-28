import math

import pint
import pytest
import regex as re

from core.builder.context.quantities import PhysicsQuantity, QuantityRange, QuantityList


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
        pos = PhysicsQuantity.construct(1.55, 'kg').approximate(2).mag()
        neg = PhysicsQuantity.construct(-1.55, 'kg').approximate(2).mag()
        assert pos == -neg, f"asymmetric rounding: {pos} vs {neg}"

    def test_zero_magnitude(self):
        m = PhysicsQuantity.construct(0.0, 'kg')
        assert m.approximate(3).mag() == 0.0

    def test_significant_figures_one(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        assert m.approximate(1).mag() == 100.0

    def test_significant_figures_three(self):
        m = PhysicsQuantity.construct(123.456, 'kg')
        assert m.approximate(3).mag() == 123.0


# --- PhysicsQuantity.mag() -------------------------------------------------


class TestMag:
    """
    `mag` is a thin accessor for the underlying pint magnitude. It returns
    whatever numeric type pint stores (int, float, or numpy scalar after
    operations like np.floor/np.ceil).
    """

    def test_int_construction(self):
        assert PhysicsQuantity.construct(7, 'kg').mag() == 7

    def test_float_construction(self):
        assert PhysicsQuantity.construct(5.5, 'kg').mag() == pytest.approx(5.5)

    def test_negative(self):
        assert PhysicsQuantity.construct(-3.7, 'kg').mag() == pytest.approx(-3.7)

    def test_dimensionless(self):
        assert PhysicsQuantity.construct(2.5, '').mag() == pytest.approx(2.5)

    def test_after_unit_conversion(self):
        """`to()` may change int -> float as a side effect of conversion."""
        kg = PhysicsQuantity.construct(1, 'kilogram')
        assert kg.to('gram').mag() == pytest.approx(1000)

    def test_mag_does_not_carry_units(self):
        """The bare magnitude is a number, not a pint Quantity."""
        m = PhysicsQuantity.construct(5, 'kg')
        assert not hasattr(m.mag(), 'units')


# --- PhysicsQuantity.floor / .ceil --------------------------------------


class TestFloorCeil:
    """
    `floor` and `ceil` round the magnitude toward -inf and +inf respectively,
    keeping the unit. They return a new PhysicsQuantity; metadata is dropped
    because the result is a different quantity from the input.
    """

    def test_floor_positive(self):
        m = PhysicsQuantity.construct(5.7, 'kg')
        assert m.floor().mag() == pytest.approx(5)

    def test_ceil_positive(self):
        m = PhysicsQuantity.construct(5.3, 'kg')
        assert m.ceil().mag() == pytest.approx(6)

    def test_floor_negative_rounds_toward_neg_inf(self):
        """floor(-2.3) is -3, not -2 (toward -inf, not toward zero)."""
        m = PhysicsQuantity.construct(-2.3, 'meter')
        assert m.floor().mag() == pytest.approx(-3)

    def test_ceil_negative_rounds_toward_pos_inf(self):
        """ceil(-2.3) is -2, not -3 (toward +inf, not toward zero)."""
        m = PhysicsQuantity.construct(-2.3, 'meter')
        assert m.ceil().mag() == pytest.approx(-2)

    def test_floor_of_integer(self):
        m = PhysicsQuantity.construct(5.0, 'kg')
        assert m.floor().mag() == pytest.approx(5)

    def test_ceil_of_integer(self):
        m = PhysicsQuantity.construct(5.0, 'kg')
        assert m.ceil().mag() == pytest.approx(5)

    def test_floor_of_zero(self):
        m = PhysicsQuantity.construct(0, 'kg')
        assert m.floor().mag() == pytest.approx(0)

    def test_ceil_of_zero(self):
        m = PhysicsQuantity.construct(0, 'kg')
        assert m.ceil().mag() == pytest.approx(0)

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
        assert m.floor().ceil().mag() == pytest.approx(5)


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
        assert r.minimum.mag() == pytest.approx(95)
        assert r.maximum.mag() == pytest.approx(105)

    def test_negative_value(self):
        """For x < 0, the result is still ordered (min < max)."""
        m = PhysicsQuantity.construct(-100, 'meter')
        r = m.widen(0.05)
        assert r.minimum.mag() == pytest.approx(-105)
        assert r.maximum.mag() == pytest.approx(-95)

    def test_large_factor_crosses_zero(self):
        """value >= 1 produces a range crossing zero."""
        m = PhysicsQuantity.construct(100, 'meter')
        r = m.widen(1.5)
        assert r.minimum.mag() == pytest.approx(-50)
        assert r.maximum.mag() == pytest.approx(250)

    def test_zero_value(self):
        """widen on x == 0 gives a degenerate range at zero."""
        m = PhysicsQuantity.construct(0, 'meter')
        r = m.widen(0.1)
        assert r.minimum.mag() == 0
        assert r.maximum.mag() == 0

    def test_zero_factor(self):
        """widen(0) gives a degenerate range at the original value."""
        m = PhysicsQuantity.construct(42, 'meter')
        r = m.widen(0)
        assert r.minimum.mag() == pytest.approx(42)
        assert r.maximum.mag() == pytest.approx(42)

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
        assert r.minimum.mag() == pytest.approx(0.9)
        assert r.maximum.mag() == pytest.approx(3.1)

    def test_widen_negative_range(self):
        """A negative-valued range must widen, not narrow."""
        a = PhysicsQuantity.construct(-3, 'kg')
        b = PhysicsQuantity.construct(-1, 'kg')
        r = QuantityRange(a, b).widen(0.1)
        assert r.minimum.mag() == pytest.approx(-3.1)
        assert r.maximum.mag() == pytest.approx(-0.9)

    def test_widen_zero_centred_range(self):
        """Range straddling zero widens symmetrically."""
        a = PhysicsQuantity.construct(-1, 'kg')
        b = PhysicsQuantity.construct(1, 'kg')
        r = QuantityRange(a, b).widen(0.5)
        assert r.minimum.mag() == pytest.approx(-1.5)
        assert r.maximum.mag() == pytest.approx(1.5)

    def test_widen_large_factor_allowed(self, m1, m3):
        """value >= 1 is now permitted; the range simply grows substantially."""
        r = QuantityRange(m1, m3).widen(1.5)
        # Centre 2, half-width 1, scaled by 2.5 -> half-width 2.5
        assert r.minimum.mag() == pytest.approx(-0.5)
        assert r.maximum.mag() == pytest.approx(4.5)

    def test_widen_negative_value_rejected(self, m1, m3):
        """widen(-0.1) would contract; reject so 'widen' stays honest about its name."""
        with pytest.raises(AssertionError, match="non-negative"):
            QuantityRange(m1, m3).widen(-0.1)

    def test_widen_identity(self, m1, m3):
        """widen(0) returns an equivalent range."""
        r = QuantityRange(m1, m3).widen(0)
        assert r.minimum.mag() == pytest.approx(1)
        assert r.maximum.mag() == pytest.approx(3)

    def test_widen_degenerate_range(self):
        """A range with min==max stays degenerate; half-width is zero."""
        a = PhysicsQuantity.construct(5, 'kg')
        r = QuantityRange(a, a).widen(0.1)
        assert r.minimum.mag() == pytest.approx(5)
        assert r.maximum.mag() == pytest.approx(5)


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

    def test_with_unit_uses_qty(self):
        m = PhysicsQuantity.construct(5, 'kg')
        assert str(m).startswith(r'\qty{')

    def test_si_extra_appears_in_output(self):
        m = PhysicsQuantity.construct(
            5, 'kg', si_extra={'round-mode': 'figures'},
        )
        assert 'round-mode=figures' in str(m)


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


# --- PhysicsConstant -----------------------------------------------------


class TestPhysicsConstant:
    """Smoke tests for the PhysicsConstant subclass."""

    @pytest.fixture
    def g(self):
        from core.builder.context.quantities.constant import PhysicsConstant
        from pint import UnitRegistry as u
        return PhysicsConstant(
            'gforce', u.Quantity(9.80665, 'meter / second^2'), digits=2,
        )

    def test_full(self, g):
        assert r'\qty{' in g.full
        assert r'\meter' in g.full

    def test_approx(self, g):
        """g with 2 digits rounds to 9.8 m/s^2."""
        assert g.approx.mag() == pytest.approx(9.8)

    def test_full_approx(self, g):
        """Previously crashed with `ValueError: Invalid format specifier`."""
        rendered = g.full_approx
        assert r'\qty{' in rendered
        assert '9.8' in rendered