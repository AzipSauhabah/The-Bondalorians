from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from bondalorians.pricing.curve_builder import DiscountCurve


def price_from_zspread(
    times: list[float],
    cashflows: list[float],
    curve: DiscountCurve,
    zspread_bps: float,
) -> float:
    """Present value of cashflows using the curve plus a continuous Z-spread."""

    t = np.asarray(times, dtype=float)
    cf = np.asarray(cashflows, dtype=float)

    if t.ndim != 1 or cf.ndim != 1 or len(t) != len(cf) or len(t) == 0:
        raise ValueError("Times and cashflows must be non-empty arrays of equal length.")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(cf)):
        raise ValueError("Times and cashflows must be finite.")
    if np.any(t < 0):
        raise ValueError("Cashflow times cannot be negative.")

    spread = zspread_bps / 10000.0
    dfs = np.array([curve.discount_factor(x) for x in t])

    return float(np.sum(cf * dfs * np.exp(-spread * t)))


def calculate_zspread(
    times: list[float],
    cashflows: list[float],
    dirty_price: float,
    curve: DiscountCurve,
) -> float:
    """
    Solve the constant continuously compounded spread in basis points.

    The input price must be DIRTY (including accrued interest).
    """
    if not np.isfinite(dirty_price) or dirty_price <= 0:
        raise ValueError("Dirty price must be positive and finite.")

    def objective(spread: float) -> float:
        return (
            price_from_zspread(times, cashflows, curve, spread * 10000)
            - dirty_price
        )

    lower, upper = -0.50, 2.00

    if objective(lower) * objective(upper) > 0:
        raise ValueError("Z-spread root not bracketed; check price and curve.")

    return float(brentq(objective, lower, upper) * 10000)
