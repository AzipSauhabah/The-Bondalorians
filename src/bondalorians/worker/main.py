"""Worker : consomme une file de taches de valorisation (SQLite data/jobs.db).

Le GUI depose des jobs ; le worker les prend un par un (exclusion mutuelle,
donc plusieurs containers worker possibles), appelle l'orchestrateur et
ecrit le statut. Pas besoin de Celery/Redis pour le hackathon : SQLite
suffit, se conteneurise, et survit au redemarrage via le volume ./data.

Lancement : python -m bondalorians.worker.main (ou docker compose up worker)
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DOSSIER = Path(__file__).resolve().parents[2] / "data"
DB = DOSSIER / "jobs.db"


def init_db() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issuer TEXT, sector TEXT, currency TEXT, rating TEXT,
            seniority TEXT, coupon_pct REAL, maturity_years REAL,
            callable INTEGER, esg_label INTEGER,
            statut TEXT NOT NULL DEFAULT 'en_attente',
            resultat TEXT, cree_le TEXT, fini_le TEXT
        )
        """
    )
    con.commit()
    con.close()


def deposer_job(cible: dict) -> int:
    """Deposer une demande de valorisation dans la file."""
    init_db()
    con = sqlite3.connect(DB)
    curseur = con.execute(
        """
        INSERT INTO jobs (issuer, sector, currency, rating, seniority,
                          coupon_pct, maturity_years, callable, esg_label, cree_le)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cible.get("issuer", "CIBLE"), cible.get("sector", "Infrastructure"),
            cible.get("currency", "EUR"), cible.get("rating", "BBB"),
            cible.get("seniority", "Senior"), cible.get("coupon_pct", 3.5),
            cible.get("maturity_years", 5.0), int(cible.get("callable", False)),
            int(cible.get("esg_label", False)), time.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    con.commit()
    job_id = curseur.lastrowid
    con.close()
    return int(job_id)


def lister_jobs(limit: int = 20) -> list[dict]:
    init_db()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    lignes = con.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [dict(l) for l in lignes]


def _job_en_dict(ligne: sqlite3.Row) -> dict:
    return {
        "issuer": ligne["issuer"], "issuer_group": "CIBLE",
        "sector": ligne["sector"], "currency": ligne["currency"],
        "rating": ligne["rating"], "seniority": ligne["seniority"],
        "coupon_pct": ligne["coupon_pct"], "maturity_years": ligne["maturity_years"],
        "callable": bool(ligne["callable"]), "esg_label": bool(ligne["esg_label"]),
    }


def prendre_job() -> tuple[int, dict] | None:
    """Prendre un job 'en_attente' et le passer 'en_cours' (exclusion mutuelle)."""
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN IMMEDIATE")
    ligne = con.execute(
        "SELECT * FROM jobs WHERE statut = 'en_attente' ORDER BY id LIMIT 1"
    ).fetchone()
    if ligne:
        con.execute("UPDATE jobs SET statut = 'en_cours' WHERE id = ?", (ligne["id"],))
    con.commit()
    con.close()
    return (ligne["id"], _job_en_dict(ligne)) if ligne else None


def terminer_job(job_id: int, statut: str, resultat: dict | str) -> None:
    con = sqlite3.connect(DB)
    con.execute(
        "UPDATE jobs SET statut = ?, resultat = ?, fini_le = ? WHERE id = ?",
        (statut, json.dumps(resultat, ensure_ascii=False, default=str),
         time.strftime("%Y-%m-%d %H:%M:%S"), job_id),
    )
    con.commit()
    con.close()


def boucle() -> None:
    """La boucle : prendre -> valoriser -> ecrire. Ctrl+C pour arreter."""
    from bondalorians.agent.orchestrateur import valoriser

    init_db()
    url_mcp = os.environ.get("MCP_URL", "http://localhost:8000/mcp")
    cle = os.environ.get("TEAM_KEY", "")
    print(f"Worker pret (MCP : {url_mcp}). Ctrl+C pour arreter.", flush=True)
    while True:
        job = prendre_job()
        if not job:
            time.sleep(1)
            continue
        job_id, cible = job
        print(f"[worker] job #{job_id} : {cible['issuer']}", flush=True)
        try:
            rapport = valoriser(cible, url_mcp, cle)
            terminer_job(job_id, "termine", {
                "nb_appels_llm": rapport["nb_appels_llm"],
                "verdict": rapport["verdict"]["verdict"],
                "summary": (rapport.get("explication") or "")[:300],
            })
            print(f"[worker] job #{job_id} termine", flush=True)
        except Exception as exc:  # un job rate ne tue pas le worker
            terminer_job(job_id, "erreur", f"{type(exc).__name__}: {exc}")
            print(f"[worker] job #{job_id} en erreur : {exc}", flush=True)


if __name__ == "__main__":
    boucle()
