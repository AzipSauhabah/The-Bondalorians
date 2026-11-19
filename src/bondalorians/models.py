from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BondRequest:
    issuer: str
    issuer_group: str
    sector: str
    currency: str
    rating: str
    seniority: str
    coupon_pct: float
    maturity_years: float
    callable: bool = False
    esg_label: bool = False
    valuation_date: str = "2026-11-09"
    nominal: float = 100.0

    def to_dict(self) -> dict:
        return asdict(self)
