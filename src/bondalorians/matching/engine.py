from __future__ import annotations

import pandas as pd

from bondalorians.models import BondRequest

RATING_ORDER = {
    "AAA": 1, "AA": 2, "A": 3, "BBB": 4, "BB": 5,
    "B": 6, "CCC": 7, "CC": 8, "C": 9, "D": 10,
}

WEIGHTS = {
    "maturity": 0.20,
    "coupon": 0.10,
    "rating": 0.20,
    "sector": 0.15,
    "issuer_group": 0.10,
    "seniority": 0.10,
    "optionality": 0.10,
    "esg": 0.05,
}


def rank_comparables(
    request: BondRequest,
    universe: pd.DataFrame,
    top_n: int = 8,
) -> pd.DataFrame:
    """Rank same-currency bonds with transparent structural similarity scores."""

    required = {
        "bond_id", "currency", "seniority", "maturity_years",
        "coupon_pct", "rating", "sector", "issuer_group",
        "callable", "esg_label", "liquidity_score",
    }
    missing = required - set(universe.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    candidates = universe[
        universe["currency"].eq(request.currency)
        & universe["bond_id"].notna()
    ].copy()

    if candidates.empty:
        return candidates.assign(
            similarity_score=pd.Series(dtype=float),
            weight=pd.Series(dtype=float),
            rationale=pd.Series(dtype=str),
        )

    target_rating = RATING_ORDER.get(request.rating)
    if target_rating is None:
        raise ValueError(f"Unsupported target rating: {request.rating}")

    candidate_ratings = candidates["rating"].map(RATING_ORDER)
    candidates = candidates[candidate_ratings.notna()].copy()
    candidate_ratings = candidates["rating"].map(RATING_ORDER)

    candidates["d_maturity"] = (
        (candidates["maturity_years"] - request.maturity_years).abs()
        / max(request.maturity_years, 1.0)
    ).clip(upper=2)

    candidates["d_coupon"] = (
        (candidates["coupon_pct"] - request.coupon_pct).abs() / 5.0
    ).clip(upper=2)

    candidates["d_rating"] = (
        (candidate_ratings - target_rating).abs() / 9.0
    )

    candidates["d_sector"] = (
        candidates["sector"] != request.sector
    ).astype(float)

    candidates["d_issuer_group"] = (
        candidates["issuer_group"] != request.issuer_group
    ).astype(float)

    candidates["d_seniority"] = (
        candidates["seniority"] != request.seniority
    ).astype(float)

    candidates["d_option"] = (
        candidates["callable"] != request.callable
    ).astype(float)

    candidates["d_esg"] = (
        candidates["esg_label"] != request.esg_label
    ).astype(float)

    candidates["distance"] = (
        WEIGHTS["maturity"] * candidates["d_maturity"]
        + WEIGHTS["coupon"] * candidates["d_coupon"]
        + WEIGHTS["rating"] * candidates["d_rating"]
        + WEIGHTS["sector"] * candidates["d_sector"]
        + WEIGHTS["issuer_group"] * candidates["d_issuer_group"]
        + WEIGHTS["seniority"] * candidates["d_seniority"]
        + WEIGHTS["optionality"] * candidates["d_option"]
        + WEIGHTS["esg"] * candidates["d_esg"]
    )

    candidates["similarity_score"] = (
        1 - candidates["distance"].clip(0, 1)
    ) * 100

    candidates["liquidity_score"] = (
        pd.to_numeric(candidates["liquidity_score"], errors="coerce")
        .fillna(0)
        .clip(0, 1)
    )

    candidates["weight"] = (
        candidates["similarity_score"].clip(lower=1)
        * candidates["liquidity_score"]
    )

    def explain(row: pd.Series) -> str:
        reasons = ["same currency"]
        criteria = [
            ("d_maturity", "close maturity", "maturity gap"),
            ("d_coupon", "close coupon", "coupon gap"),
            ("d_rating", "same rating", "rating difference"),
            ("d_sector", "same sector", "different sector"),
            ("d_issuer_group", "same issuer group", "different issuer group"),
            ("d_seniority", "same seniority", "seniority mismatch"),
            ("d_option", "same callability", "optionality mismatch"),
            ("d_esg", "same ESG status", "ESG status mismatch"),
        ]
        for column, good, bad in criteria:
            reasons.append(good if row[column] == 0 else bad)
        return "; ".join(reasons)

    candidates["rationale"] = candidates.apply(explain, axis=1)

    return (
        candidates.sort_values(
            ["distance", "liquidity_score"],
            ascending=[True, False],
        )
        .head(top_n)
        .reset_index(drop=True)
    )
