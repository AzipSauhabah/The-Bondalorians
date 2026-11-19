from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ZeroRatePoint:
    tenor_years: float
    zero_rate_pct: float


class DiscountCurve:
    """Discount curve built from continuously compounded zero rates."""

    def __init__(self, points: list[ZeroRatePoint]):
        if not points:
            raise ValueError("At least one zero-rate point is required.")

        ordered = sorted(points, key=lambda p: p.tenor_years)

        tenors = np.array([p.tenor_years for p in ordered], dtype=float)
        rates = np.array([p.zero_rate_pct for p in ordered], dtype=float)

        if np.any(tenors <= 0):
            raise ValueError("Tenors must be strictly positive.")
        if np.any(np.diff(tenors) <= 0):
            raise ValueError("Tenors must be unique.")
        if not np.all(np.isfinite(rates)):
            raise ValueError("Zero rates must be finite.")

        self.tenors = np.concatenate(([0.0], tenors))
        self.zero_rates = rates
        self.discount_factors = np.concatenate(
            ([1.0], np.exp(-(rates / 100.0) * tenors))
        )

        self._log_discount_factors = np.log(self.discount_factors)

    def discount_factor(self, time_years: float) -> float:
        if not np.isfinite(time_years) or time_years < 0:
            raise ValueError("Time must be finite and non-negative.")

        if time_years > self.tenors[-1]:
            raise ValueError(
                f"Curve extrapolation is not allowed: {time_years}Y "
                f"exceeds maximum tenor {self.tenors[-1]}Y."
            )

        log_df = np.interp(
            time_years,
            self.tenors,
            self._log_discount_factors,
        )
        return float(np.exp(log_df))


def build_discount_curve(points: list[ZeroRatePoint]) -> DiscountCurve:
    """
    Build a discount curve from zero rates.

    IMPORTANT:
    Input rates must already be zero rates, not par swap rates.
    Rates are interpreted as continuously compounded percentages.
    """
    return DiscountCurve(points)
