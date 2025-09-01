import pint
import pytest

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
def length():
    return PhysicsQuantity.construct(2, 'm', symbol='L')


class TestExpression:
    def test_sum(self, mass1, mass2):
        expected = PhysicsQuantity.construct(8000, 'gram')
        computed = (mass1 + mass2).to('gram')
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"


    def test_sum_fails(self, mass1, length):
        with pytest.raises(pint.errors.DimensionalityError):
            _ = mass1 + length


class TestAngles:
    def test_angle(self, mass1, mass2):
        expected = PhysicsQuantity.construct(1, 'rad', symbol=r'\omega')


class TestRange:
    def test_masses(self, mass1, mass2):
        expected = r'\qtyrange{1}{7}{\kilo\gram}'
        computed = rf'{QuantityRange(mass1, mass2)}'
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"


class TestList:
    def test_masses(self, mass1, mass2, mass_mega):
        expected = r'\qtylist{1;7;96.7}{\kilo\gram}'
        computed = rf'{QuantityList(mass1, mass2, mass_mega)}'
        assert expected == computed, \
            f"Expected {expected}, computed {computed}"
