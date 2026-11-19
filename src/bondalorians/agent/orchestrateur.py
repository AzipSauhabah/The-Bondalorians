"""Orchestrateur Mistral : revue des risques puis explicabilite, evidence-based.

Rappel du cahier des charges (README du depot) :
- le moteur quantitatif fait autorite (aucun chiffre invente par le LLM) ;
- la revue des risques CHALLENGE l'estimation (divergences, dispersion) ;
- l'explicabilite s'appuie UNIQUEMENT sur le dossier de preuves ;
- 3 a 5 appels LLM max par valorisation.

Le workflow complete le graphe LangGraph existant (retrieve -> match ->
price -> explain) par les DEUX etapes LLM critiques. Ces deux agents sont
d'abord codes ici (autonomes, testables), puis on les reprendra tels
quels dans Mistral Studio (Workflows) apres le webinaire.

Sans MISTRAL_API_KEY, valoriser() retourne le dossier de preuves avec la
revue marquee NON_EXECUTE : la pile tourne sans reseau.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from bondalorians.agent.client_mcp import appeler_outil, resultat_en_dict

load_dotenv()

MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")

PROMPT_REVUE = (
    "Tu es la revue des risques d'une estimation de Z-spread. On te donne "
    "la cible, l'estimation et son panel de comparables. Challenge l'analyse : "
    "divergences, dispersion du panel, extrapolation, qualite des donnees. "
    "Reponds par un JSON exact sans texte autour : "
    '{"verdict": "OK"|"DIVERGENCE", "synthese": "...", "points": ["..."]}'
)

PROMPT_EXPLICABILITE = (
    "Tu es l'agent d'explicabilite. A partir UNIQUEMENT du dossier de preuves "
    "fourni (cible, panel, estimation, verdict de la revue), redige en francais "
    "un rapport concis et auditable : methodologie, comparables retenus, "
    "resultat en bps, limites. N'invente AUCUN fait, ne modifie aucun calcul."
)


def appeler_llm(systeme: str, utilisateur: str) -> str:
    """Un appel Mistral (import tardif : tourne aussi sans cle)."""
    from mistralai import Mistral

    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    reponse = client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {"role": "system", "content": systeme},
            {"role": "user", "content": utilisateur},
        ],
    )
    return reponse.choices[0].message.content or ""


def extraire_json(texte: str) -> dict:
    """Extraire le premier objet JSON d'une reponse de LLM."""
    debut, fin = texte.find("{"), texte.rfind("}")
    return json.loads(texte[debut : fin + 1]) if (debut, fin) != (-1, -1) else {}


def valoriser(cible: dict, url_mcp: str, cle_mcp: str = "") -> dict:
    """Cycle complet : preuves (MCP) -> revue LLM -> explication LLM -> audit."""
    nb_appels_llm = 0

    # 1. Preuves : estimation + panel, tout est deterministe (zero LLM)
    estimation = resultat_en_dict(appeler_outil(url_mcp, "pricer_cible", {"cible": cible}, cle_mcp))
    panel = resultat_en_dict(appeler_outil(url_mcp, "chercher_comparables", {"cible": cible}, cle_mcp))
    preuves = {"cible": cible, "estimation": estimation, "panel": panel}

    # 2. Revue des risques (1er appel LLM de la chaine)
    verdict = {"verdict": "NON_EXECUTE", "synthese": "revue non executee (pas de MISTRAL_API_KEY)", "points": []}
    if os.environ.get("MISTRAL_API_KEY"):
        texte = appeler_llm(PROMPT_REVUE, json.dumps(preuves, ensure_ascii=False, default=str))
        verdict = extraire_json(texte)
        nb_appels_llm += 1

    # 3. Explicabilite (2e appel LLM), puis horodatage comptable
    rapport = {
        "cible": cible,
        "date": datetime.now(timezone.utc).isoformat(),
        "estimation": estimation,
        "panel": panel,
        "verdict": verdict,
        "nb_appels_llm": nb_appels_llm,
    }
    if os.environ.get("MISTRAL_API_KEY"):
        rapport["explication"] = appeler_llm(
            PROMPT_EXPLICABILITE, json.dumps(preuves | {"verdict": verdict}, ensure_ascii=False, default=str)
        )
        rapport["nb_appels_llm"] = nb_appels_llm + 1

    # 4. Tracabilite : ecriture de la piste d'audit via l'outil MCP
    appeler_outil(url_mcp, "enregistrer_audit", {"rapport": rapport}, cle_mcp)
    return rapport
