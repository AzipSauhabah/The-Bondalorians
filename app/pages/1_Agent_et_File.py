"""Page Agent & File : revue LLM, explicabilite, et file de jobs du worker.

Se lit comme une demo de l'architecture complete :
  choix de la cible -> job dans la file -> worker -> orchestrateur ->
  MCP (calculs deterministes) -> revue + explication (Mistral) -> audit.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))

import pandas as pd
import streamlit as st

from bondalorians.worker.main import lister_jobs, deposer_job

st.set_page_config(page_title="Agent & File", page_icon="🤖", layout="wide")
st.title("🤖 Agent, file de jobs et audit")
st.caption("Le worker execute l'orchestrateur ; les calculs restent dans le moteur Python.")

onglet_df, onglet_audit = st.tabs(["File de valorisations", "Piste d'audit"])

with onglet_df:
    with st.form("nouvelle_cible"):
        colA, colB = st.columns(2)
        issuer = colA.text_input("Emetteur (cible)", "OMEGA_INFRA")
        rating = colA.selectbox("Rating", ["AAA", "AA", "A", "BBB", "BB", "B"], index=3)
        coupon = colA.number_input("Coupon (%)", 0.0, 15.0, 3.5, 0.05)
        sector = colB.selectbox("Secteur", ["Utilities", "Infrastructure", "Banking", "Transport", "Telecom"])
        seniority = colB.selectbox("Seniorite", ["Senior", "Subordinated"])
        maturity = colB.number_input("Maturite (annees)", 0.5, 30.0, 5.0, 0.5)
        if st.form_submit_button("Deposer dans la file", type="primary"):
            job_id = deposer_job({
                "issuer": issuer, "sector": sector, "currency": "EUR",
                "rating": rating, "seniority": seniority,
                "coupon_pct": coupon, "maturity_years": maturity,
            })
            st.success(f"Job #{job_id} depose. Le worker le prend : docker compose up worker (ou python -m bondalorians.worker.main).")

    jobs = lister_jobs()
    if jobs:
        st.dataframe(pd.DataFrame(jobs), use_container_width=True)
    else:
        st.info("Aucun job pour le moment.")

with onglet_audit:
    rep_audit = RACINE / "data" / "audit"
    rapports = sorted(rep_audit.glob("*.json"), reverse=True) if rep_audit.exists() else []
    if rapports:
        choix = st.selectbox("Rapport d'audit", rapports, format_func=lambda p: p.name)
        st.json(json.loads(choix.read_text(encoding="utf-8")))
    else:
        st.info("Aucun rapport d'audit : demarrer le serveur MCP puis lancer une valorisation.")
