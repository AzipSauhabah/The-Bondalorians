from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20261112)
DATES = [pd.Timestamp("2026-10-30"), pd.Timestamp("2026-11-12")]
TENORS = np.array([0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20], dtype=float)

ISSUERS = [
    ("ALPHA_ENERGY", "Utilities", "BBB"),
    ("BETA_POWER", "Utilities", "BBB"),
    ("GAMMA_GRID", "Utilities", "A"),
    ("DELTA_INFRA", "Infrastructure", "BBB"),
    ("EPSILON_ENERGY", "Energy", "BB"),
    ("ZETA_POWER", "Utilities", "A"),
    ("ETA_TRANSIT", "Transport", "BBB"),
    ("THETA_ENERGY", "Energy", "BBB"),
    ("IOTA_BANK", "Banking", "BBB"),
    ("KAPPA_UTIL", "Utilities", "BBB"),
    ("LAMBDA_TELECOM", "Telecom", "A"),
    ("MU_AUTO", "Automotive", "BB"),
    ("NU_REAL_ESTATE", "Real Estate", "BBB"),
    ("XI_PHARMA", "Healthcare", "A"),
    ("OMICRON_RETAIL", "Retail", "BB"),
    ("PI_TECH", "Technology", "A"),
    ("RHO_INFRA", "Infrastructure", "BBB"),
    ("SIGMA_BANK", "Banking", "A"),
    ("TAU_ENERGY", "Energy", "BB"),
    ("UPSILON_TRANSPORT", "Transport", "BBB"),
]

RATING_SPREAD = {
    "AAA": 25, "AA": 45, "A": 70, "BBB": 120,
    "BB": 210, "B": 350, "CCC": 600,
}
SECTORS = ["Utilities", "Infrastructure", "Energy", "Transport",
           "Banking", "Telecom", "Automotive", "Real Estate",
           "Healthcare", "Retail", "Technology"]
RATINGS = list(RATING_SPREAD)


def make_curve(date: pd.Timestamp, shift_bps: float) -> tuple[list[dict], list[dict]]:
    base = np.array([1.85, 1.90, 1.98, 2.05, 2.12, 2.18, 2.30, 2.45, 2.60, 2.68])
    curvature = np.array([0, 2, 4, 5, 6, 7, 8, 9, 10, 10])
    zero = base + shift_bps / 100 + curvature / 100
    # Synthetic par swap quotes are deliberately distinct from zero rates.
    par = zero + np.array([0.01, 0.015, 0.025, 0.035, 0.045,
                           0.055, 0.065, 0.075, 0.085, 0.09])
    zero_rows, par_rows = [], []
    for tenor, zr, pr in zip(TENORS, zero, par):
        zero_rows.append({
            "valuation_date": date.date().isoformat(),
            "currency": "EUR",
            "curve_name": "EUR_SYNTHETIC_ZERO",
            "tenor_years": tenor,
            "zero_rate_pct": round(float(zr), 6),
            "rate_type": "CONTINUOUS_ZERO",
            "source": "SYNTHETIC",
        })
        par_rows.append({
            "valuation_date": date.date().isoformat(),
            "currency": "EUR",
            "curve_name": "EUR_SWAP_6M_SYNTHETIC",
            "tenor_years": tenor,
            "par_swap_rate_pct": round(float(pr), 6),
            "floating_index": "EURIBOR_6M",
            "source": "SYNTHETIC",
        })
    return zero_rows, par_rows


curve_zero, curve_par = [], []
for i, date in enumerate(DATES):
    z, p = make_curve(date, shift_bps=[0, 8][i])
    curve_zero.extend(z)
    curve_par.extend(p)

pd.DataFrame(curve_zero).to_csv(OUT / "zero_curves.csv", index=False)
pd.DataFrame(curve_par).to_csv(OUT / "eur_swap6m_curve.csv", index=False)

# Issuer-level spread adjustments create realistic within-sector clustering.
issuer_adjustments = {
    name: float(RNG.normal(0, 18)) for name, _, _ in ISSUERS
}

master = []
for i in range(500):
    issuer, sector, base_rating = ISSUERS[i % len(ISSUERS)]
    rating = base_rating
    if RNG.random() < 0.16:
        rating = RATINGS[max(0, min(len(RATINGS)-1,
                                   RATINGS.index(base_rating) + int(RNG.choice([-1, 1]))))]
    seniority = RNG.choice(
        ["Senior Secured", "Senior Unsecured", "Subordinated"],
        p=[0.18, 0.67, 0.15],
    )
    maturity_years = float(RNG.uniform(0.75, 18))
    maturity_date = DATES[0] + pd.to_timedelta(maturity_years * 365.25, unit="D")
    coupon = float(RNG.uniform(1.0, 6.2))
    frequency = int(RNG.choice([1, 2], p=[0.12, 0.88]))
    callable_bond = bool(RNG.random() < 0.12)
    esg = bool(RNG.random() < 0.25)
    currency = "EUR" if RNG.random() < 0.92 else "USD"

    seniority_adj = {
        "Senior Secured": -12,
        "Senior Unsecured": 0,
        "Subordinated": 75,
    }[seniority]
    rating_spread = RATING_SPREAD[rating]
    sector_adj = {"Banking": 10, "Energy": 15, "Real Estate": 30}.get(sector, 0)
    true_spread = (
        rating_spread + seniority_adj + sector_adj
        + issuer_adjustments[issuer] + RNG.normal(0, 12)
    )
    if callable_bond:
        true_spread += 20
    if currency == "USD":
        true_spread += 10

    master.append({
        "bond_id": f"SYN{i+1:04d}",
        "issuer": issuer,
        "issuer_group": issuer.split("_")[0],
        "sector": sector,
        "currency": currency,
        "rating": rating,
        "seniority": seniority,
        "coupon_pct": round(coupon, 4),
        "issue_date": (DATES[0] - pd.Timedelta(days=int(RNG.integers(365, 365*8)))).date().isoformat(),
        "maturity_date": maturity_date.date().isoformat(),
        "maturity_years": round(maturity_years, 6),
        "coupon_frequency": frequency,
        "day_count": "30/360",
        "callable": callable_bond,
        "esg_label": esg,
        "nominal": 100.0,
        "true_spread_bps": round(float(true_spread), 4),
        "liquidity_score": round(float(RNG.uniform(0.35, 0.99)), 4),
        "data_status": "SYNTHETIC",
    })

bonds = pd.DataFrame(master)
bonds.drop(columns=["true_spread_bps"]).to_csv(OUT / "bonds_master.csv", index=False)

observations = []
for date_idx, date in enumerate(DATES):
    curve = pd.DataFrame(curve_zero)
    curve = curve[curve.valuation_date == date.date().isoformat()]
    curve_t = curve.tenor_years.to_numpy()
    curve_r = curve.zero_rate_pct.to_numpy()

    for row in bonds.itertuples(index=False):
        T = max(0.25, (pd.Timestamp(row.maturity_date) - date).days / 365.25)
        if T <= 0:
            continue
        periods = max(1, int(np.ceil(T * row.coupon_frequency)))
        times = np.arange(1, periods + 1, dtype=float) * T / periods
        coupon_cf = 100 * row.coupon_pct / 100 / row.coupon_frequency
        cashflows = np.full(periods, coupon_cf)
        cashflows[-1] += 100

        zero_rates = np.interp(times, curve_t, curve_r, left=curve_r[0], right=curve_r[-1])
        zspread = row.true_spread_bps / 10000
        discount_factors = np.exp(-(zero_rates / 100 + zspread) * times)
        dirty_price = float(np.sum(cashflows * discount_factors))

        # Synthetic accrued interest: deterministic fraction of the coupon period.
        accrued_fraction = float(RNG.uniform(0.05, 0.95))
        accrued = coupon_cf * accrued_fraction
        clean_price = dirty_price - accrued

        observations.append({
            "bond_id": row.bond_id,
            "valuation_date": date.date().isoformat(),
            "currency": row.currency,
            "price_clean": round(clean_price, 6),
            "price_dirty": round(dirty_price, 6),
            "accrued_interest": round(accrued, 6),
            "ytm_pct": round(float(row.coupon_pct + row.true_spread_bps / 100), 6),
            "zspread_bps": round(float(row.true_spread_bps), 6),
            "market_status": "SYNTHETIC",
        })

obs = pd.DataFrame(observations)
obs.to_csv(OUT / "market_observations.csv", index=False)

# Three target cases. Ground truth is stored separately from agent inputs.
cases = [
    {
        "case_id": "CASE_SIMPLE",
        "scenario": "SIMPLE",
        "issuer": "ALPHA_ENERGY",
        "sector": "Utilities",
        "currency": "EUR",
        "rating": "BBB",
        "seniority": "Senior Unsecured",
        "coupon_pct": 3.4,
        "maturity_years": 5.0,
        "callable": False,
        "esg_label": False,
        "description": "Émission classique avec nombreux comparables proches.",
        "truth_spread_bps": 132.0,
    },
    {
        "case_id": "CASE_INTERMEDIATE",
        "scenario": "INTERMEDIATE",
        "issuer": "OMEGA_INFRA",
        "sector": "Infrastructure",
        "currency": "EUR",
        "rating": "BBB",
        "seniority": "Senior Unsecured",
        "coupon_pct": 4.1,
        "maturity_years": 8.0,
        "callable": False,
        "esg_label": True,
        "description": "Émetteur peu représenté, univers riche en comparables sectoriels.",
        "truth_spread_bps": 158.0,
    },
    {
        "case_id": "CASE_COMPLEX",
        "scenario": "COMPLEX",
        "issuer": "OMEGA_GREEN",
        "sector": "Technology",
        "currency": "EUR",
        "rating": "BB",
        "seniority": "Subordinated",
        "coupon_pct": 5.2,
        "maturity_years": 12.0,
        "callable": True,
        "esg_label": True,
        "description": "Émission hybride callable, sans comparable direct satisfaisant.",
        "truth_spread_bps": 295.0,
    },
]

case_inputs, truths = [], []
for c in cases:
    case_inputs.append({k: v for k, v in c.items() if k != "truth_spread_bps"})
    truths.append({
        "case_id": c["case_id"],
        "valuation_date": DATES[1].date().isoformat(),
        "true_zspread_bps": c["truth_spread_bps"],
        "truth_status": "SYNTHETIC_GROUND_TRUTH",
    })

pd.DataFrame(case_inputs).to_csv(OUT / "valuation_cases.csv", index=False)
pd.DataFrame(truths).to_csv(OUT / "validation_truth.csv", index=False)

dictionary = """# Synthetic bond dataset

All records are artificially generated for hackathon preparation.
They are NOT real market data and must not be represented as such.

## Files
- bonds_master.csv: static bond characteristics.
- market_observations.csv: synthetic clean/dirty prices and spreads at two dates.
- eur_swap6m_curve.csv: synthetic EURIBOR 6M par swap quotes.
- zero_curves.csv: synthetic continuously compounded zero rates used to generate prices.
- valuation_cases.csv: three target bond requests for the agent.
- validation_truth.csv: hidden benchmark truth; never expose to the pricing agent.

## Conventions and limitations
- Currency: EUR predominantly, with a small USD subset.
- Nominal: 100.
- Coupon frequency: annual or semiannual.
- Day count label: 30/360 (simplified synthetic generation).
- Prices are generated from simplified semiannual/annual cashflow schedules.
- Accrued interest is synthetic and not a QuantLib accrued-interest calculation.
- Zero rates are continuously compounded.
- Z-spread is a constant continuously compounded spread added to zero rates.
- EUR Swap 6M par quotes are separate from zero rates; do not use par quotes directly as zero rates.
- Callable and ESG features are labels; option valuation and ESG premium are not fully modelled.
- No observation is real, executable, tradable, or sourced from CDC.
"""
(OUT / "data_dictionary.md").write_text(dictionary, encoding="utf-8")

manifest = {
    "generated_at": pd.Timestamp.now().isoformat(),
    "seed": 20261112,
    "synthetic": True,
    "bonds": len(bonds),
    "observations": len(obs),
    "valuation_cases": len(cases),
    "dates": [d.date().isoformat() for d in DATES],
    "files": sorted(p.name for p in OUT.iterdir()),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps(manifest, indent=2))
print("\nFichiers générés dans :", OUT)
