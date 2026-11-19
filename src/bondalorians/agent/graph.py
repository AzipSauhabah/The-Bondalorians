from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from bondalorians.integrations.mcp_adapter import DemoMarketDataAdapter
from bondalorians.matching.engine import rank_comparables
from bondalorians.models import BondRequest
from bondalorians.pricing.engine import value_bond


class PricingState(TypedDict, total=False):
    request: dict
    universe: Any
    panel: Any
    valuation: dict
    explanation: str
    error: str


def build_graph(adapter=None):
    market_data = adapter or DemoMarketDataAdapter()

    def retrieve(state: PricingState):
        return {"universe": market_data.search_bonds()}

    def match(state: PricingState):
        request = BondRequest(**state["request"])
        panel = rank_comparables(request, state["universe"])
        return {"panel": panel}

    def price(state: PricingState):
        request = BondRequest(**state["request"])
        try:
            return {"valuation": value_bond(request, state["panel"])}
        except ValueError as exc:
            return {"error": str(exc)}

    def explain(state: PricingState):
        if state.get("error"):
            return {"explanation": state["error"]}
        v = state["valuation"]
        return {"explanation": (
            f"Estimated clean price {v['clean_price']:.3f} per 100 nominal, "
            f"based on {v['panel_count']} comparable bonds. "
            f"Estimated spread: {v['estimated_spread_bps']:.1f} bps; "
            f"confidence: {v['confidence']}. Illustrative prototype result, not a tradable quote."
        )}

    graph = StateGraph(PricingState)
    graph.add_node("retrieve_market_data", retrieve)
    graph.add_node("rank_comparables", match)
    graph.add_node("calculate_price", price)
    graph.add_node("explain_result", explain)
    graph.set_entry_point("retrieve_market_data")
    graph.add_edge("retrieve_market_data", "rank_comparables")
    graph.add_edge("rank_comparables", "calculate_price")
    graph.add_edge("calculate_price", "explain_result")
    graph.add_edge("explain_result", END)
    return graph.compile()


def run_pricing(request: BondRequest) -> dict:
    app = build_graph()
    return app.invoke({"request": request.to_dict()})
