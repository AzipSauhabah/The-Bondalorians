"""Serveur MCP : expose les outils du moteur quantitatif a l'agent.

Principe du README : le LLM ne calcule rien. Ici, TOUT est deterministe :
- chercher_comparables : Ranking engine (src.bondalorians.matching.engine) ;
- pricer_cible         : le pipeline LangGraph existant (recherche → matching
                          → pricing → explication) ;
- enregistrer_audit    : piste d'audit JSON (data/audit/).

Le reste de la pile (client MCP du hackathon, Studio) appelle ces outils
comme n'importe quel serveur MCP : POST JSON-RPC sur /mcp.

Lancement : python -m bondalorians.mcp_server.server
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE / "src"))

from bondalorians.agent.graph import run_pricing          # noqa: E402
from bondalorians.data.repository import load_comparables  # noqa: E402
from bondalorians.matching.engine import rank_comparables  # noqa: E402
from bondalorians.models import BondRequest                # noqa: E402

DOSSIER_AUDIT = RACINE / "data" / "audit"

mcp = FastMCP(name="bondalorians-outils")


def _cible_depuis_dict(cible: dict) -> BondRequest:
    """Construire une BondRequest (pydantic) depuis un dict JSON."""
    return BondRequest(
        issuer=cible.get("issuer", "CIBLE"),
        issuer_group=cible.get("issuer_group", "CIBLE"),
        sector=cible.get("sector", "Infrastructure"),
        currency=cible.get("currency", "EUR"),
        rating=cible.get("rating", "BBB"),
        seniority=cible.get("seniority", "Senior"),
        coupon_pct=float(cible.get("coupon_pct", 3.5)),
        maturity_years=float(cible.get("maturity_years", 5.0)),
        callable=cible.get("callable", False),
        esg_label=bool(cible.get("esg", False)),
    )


@mcp.tool
def lister_univers() -> list[dict]:
    """Lister l'univers obligataire disponible (sans aucun spread cible)."""
    df = load_comparables()
    return json.loads(df.to_json(orient="records"))


@mcp.tool
def chercher_comparables(cible: dict, top_n: int = 8) -> dict:
    """Classer les obligations comparables d'une cible donnee.

    Pur Python, zero LLM : c'est le filtre qui economise les tokens.

    Args:
        cible: caracteristiques (issuer, sector, currency, rating,
            seniority, coupon_pct, maturity_years, callable, esg).
        top_n: nombre de comparables a retourner.
    """
    requete = _cible_depuis_dict(cible)
    panel = rank_comparables(requete, load_comparables(), top_n=top_n)
    return json.loads(panel.to_json(orient="records"))


@mcp.tool
def pricer_cible(cible: dict) -> dict:
    """Executer le workflow de valorisation complet pour une cible.

    Args:
        cible: caracteristiques de l'obligation cible (memes champs que
            chercher_comparables).
    """
    requete = _cible_depuis_dict(cible)
    return run_pricing(requete)


@mcp.tool
def enregistrer_audit(rapport: dict) -> dict:
    """Enregistrer un rapport dans la piste d'audit (data/audit/*.json).

    Args:
        rapport: rapport complet (cible, estimation, preuves, horodatage).
    """
    DOSSIER_AUDIT.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    chemin = DOSSIER_AUDIT / f"{horodatage}-{rapport.get('isin', rapport.get('issuer', 'cible'))}.json"
    chemin.write_text(json.dumps(rapport, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"enregistre": str(chemin)}


if __name__ == "__main__":
    print("Serveur MCP Bondalorians : http://0.0.0.0:8000/mcp", flush=True)
    mcp.run(transport="http", host="0.0.0.0", port=8000)
