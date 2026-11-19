from bondalorians.data.repository import load_comparables
from bondalorians.matching.engine import rank_comparables
from bondalorians.models import BondRequest
from bondalorians.pricing.engine import price_from_yield, value_bond, yield_to_maturity


def sample_request():
    return BondRequest("OMEGA_INFRA", "OMEGA", "Utilities", "EUR", "BBB", "Senior", 3.5, 5.0)


def test_yield_price_roundtrip():
    price = price_from_yield(3.5, 5.0, 3.2)
    ytm = yield_to_maturity(price, 3.5, 5.0)
    assert abs(ytm - 3.2) < 1e-8


def test_matching_keeps_currency_and_scores_seniority():
    panel = rank_comparables(sample_request(), load_comparables())

    assert not panel.empty
    assert (panel.currency == "EUR").all()
    assert "Senior" in panel.seniority.values
    assert "Subordinated" in panel.seniority.values

    senior = panel[panel.seniority == "Senior"]
    subordinated = panel[panel.seniority == "Subordinated"]

    assert not senior.empty
    assert not subordinated.empty
    assert senior.similarity_score.mean() > subordinated.similarity_score.mean()


def test_valuation_is_positive_and_explained():
    req = sample_request()
    panel = rank_comparables(req, load_comparables())
    result = value_bond(req, panel)
    assert result["clean_price"] > 0
    assert result["panel_count"] > 0
    assert result["confidence"] in {"Low", "Medium", "High"}
