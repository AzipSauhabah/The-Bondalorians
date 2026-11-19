import pytest

from bondalorians.pricing.curve_builder import (
    ZeroRatePoint,
    build_discount_curve,
)
from bondalorians.pricing.zspread import (
    calculate_zspread,
    price_from_zspread,
)


@pytest.fixture
def curve():
    return build_discount_curve([
        ZeroRatePoint(1.0, 2.0),
        ZeroRatePoint(2.0, 2.1),
        ZeroRatePoint(5.0, 2.3),
        ZeroRatePoint(10.0, 2.5),
    ])


def test_discount_factor_at_zero(curve):
    assert curve.discount_factor(0.0) == pytest.approx(1.0)


def test_discount_factor_decreases(curve):
    assert curve.discount_factor(5.0) < curve.discount_factor(1.0)


def test_zspread_roundtrip(curve):
    times = [1.0, 2.0, 3.0, 4.0, 5.0]
    cashflows = [3.0, 3.0, 3.0, 3.0, 103.0]

    expected_spread = 125.0
    dirty_price = price_from_zspread(
        times, cashflows, curve, expected_spread
    )

    calculated = calculate_zspread(
        times, cashflows, dirty_price, curve
    )

    assert calculated == pytest.approx(expected_spread, abs=1e-6)


def test_curve_rejects_extrapolation(curve):
    with pytest.raises(ValueError, match="extrapolation"):
        curve.discount_factor(15.0)
