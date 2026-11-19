"""Client MCP minimal (JSON-RPC POST) : sert a l'agent ET au worker.

La cle du hackathon part dans l'en-tete Ocp-Apim-Subscription-Key
(API Gateway CDC) ; sans cle (serveur local), aucune en-tete d'auth
n'est envoyee. La reponse peut arriver en JSON brut ou en SSE
(lignes "data: {...}") : les deux formats sont geres.
"""
from __future__ import annotations

import json

import httpx


def _en_tetes(cle: str | None) -> dict[str, str]:
    en_tetes = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
    if cle:
        en_tetes["Ocp-Apim-Subscription-Key"] = cle
    return en_tetes


def _reponse_en_dict(reponse: httpx.Response) -> dict:
    texte = reponse.text
    if texte.lstrip().startswith("{"):
        return json.loads(texte)
    for ligne in texte.splitlines():  # format SSE
        if ligne.startswith("data:"):
            return json.loads(ligne[5:].strip())
    raise ValueError(f"Reponse MCP illisible : {texte[:200]}")


def appeler_outil(url: str, nom: str, arguments: dict | None = None, cle: str | None = None) -> dict:
    """Un tools/call JSON-RPC ; renvoie la reponse complete."""
    charge = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": nom, "arguments": arguments or {}},
    }
    reponse = httpx.post(url, headers=_en_tetes(cle), json=charge, timeout=60)
    reponse.raise_for_status()
    return _reponse_en_dict(reponse)


def resultat_en_dict(reponse: dict) -> dict | list:
    """Extraire le payload JSON d'une reponse tools/call."""
    resultat = reponse.get("result") or {}
    if resultat.get("isError"):
        raise RuntimeError("Erreur outil MCP : " + json.dumps(resultat.get("content", []), ensure_ascii=False)[:300])
    texte = "\n".join(b.get("text", "") for b in resultat.get("content", []) if isinstance(b, dict))
    return json.loads(texte)


def lister_outils(url: str, cle: str | None = None) -> list[dict]:
    """tools/list : decouvrir le catalogue (debug, CI, GUI)."""
    charge = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    reponse = httpx.post(url, headers=_en_tetes(cle), json=charge, timeout=30)
    reponse.raise_for_status()
    return _reponse_en_dict(reponse).get("result", {}).get("tools", [])
