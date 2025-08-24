import pint
import pytest

from core.builder.context.quantity import PhysicsQuantity


@pytest.fixture
def mass1():
    return PhysicsQuantity.construct(1, 'kg', symbol='m')


@pytest.fixture
def mass2():
    return PhysicsQuantity.construct(7, 'kg', symbol='m')


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