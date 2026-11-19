from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from bondalorians.models import BondRequest


def yield_to_maturity(price: float, coupon_pct: float, maturity_years: float, frequency: int = 2) -> float:
    periods = max(1, round(maturity_years * frequency))
    coupon = coupon_pct / 100 * 100 / frequency
    times = np.arange(1, periods + 1)
    cashflows = np.full(periods, coupon, dtype=float)
    cashflows[-1] += 100.0
    def objective(y: float) -> float:
        return float(np.sum(cashflows / (1 + y / frequency) ** times) - price)
    return float(brentq(objective, -0.05, 1.0) * 100)


def risk_free_rate(maturity_years: float) -> float:
    """Illustrative EUR curve in percent; replace with official curve data in the hackathon."""
    tenors = np.array([0.5, 1, 2, 3, 5, 7, 10], dtype=float)
    rates = np.array([2.05, 2.00, 2.03, 2.08, 2.18, 2.28, 2.42], dtype=float)
    return float(np.interp(maturity_years, tenors, rates))


def price_from_yield(coupon_pct: float, maturity_years: float, ytm_pct: float, frequency: int = 2) -> float:
    periods = max(1, round(maturity_years * frequency))
    coupon = coupon_pct / 100 * 100 / frequency
    times = np.arange(1, periods + 1)
    cashflows = np.full(periods, coupon, dtype=float)
    cashflows[-1] += 100.0
    return float(np.sum(cashflows / (1 + ytm_pct / 100 / frequency) ** times))


def value_bond(request: BondRequest, panel: pd.DataFrame) -> dict:
    if panel.empty:
        raise ValueError("No comparable bond found after hard filters; cannot estimate a price.")
    panel = panel.copy()
    panel["ytm_pct"] = panel.apply(
        lambda r: yield_to_maturity(r.price_clean, r.coupon_pct, r.maturity_years), axis=1
    )
    panel["risk_free_pct"] = panel.maturity_years.map(risk_free_rate)
    panel["spread_bps"] = (panel.ytm_pct - panel.risk_free_pct) * 100
    weights = panel.weight.to_numpy(dtype=float)
    spreads = panel.spread_bps.to_numpy(dtype=float)
    estimated_spread_bps = float(np.average(spreads, weights=weights))
    target_rf = risk_free_rate(request.maturity_years)
    target_ytm = target_rf + estimated_spread_bps / 100
    clean_price = price_from_yield(request.coupon_pct, request.maturity_years, target_ytm)
    low_price = price_from_yield(request.coupon_pct, request.maturity_years, target_ytm + 0.25)
    high_price = price_from_yield(request.coupon_pct, request.maturity_years, target_ytm - 0.25)
    dispersion = float(np.sqrt(np.average((spreads - estimated_spread_bps) ** 2, weights=weights)))
    confidence = "High" if len(panel) >= 6 and dispersion < 45 else "Medium" if len(panel) >= 3 else "Low"
    return {
        "clean_price": clean_price,
        "estimated_spread_bps": estimated_spread_bps,
        "risk_free_pct": target_rf,
        "estimated_ytm_pct": target_ytm,
        "price_low": min(low_price, high_price),
        "price_high": max(low_price, high_price),
        "spread_dispersion_bps": dispersion,
        "confidence": confidence,
        "panel_count": len(panel),
        "panel_with_metrics": panel,
    }
