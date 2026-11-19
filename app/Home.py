from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.express as px
import streamlit as st
from bondalorians.models import BondRequest
from bondalorians.agent.graph import run_pricing
from bondalorians.db import save_run

st.set_page_config(page_title="The Bondalorians | Bond Pricing Agent", page_icon="📈", layout="wide")
st.title("📈 The Bondalorians")
st.caption("Comparable Bond Pricing Agent · Local prototype · Synthetic demonstration data")
st.warning("Prototype pédagogique : les données et la courbe sont synthétiques. Aucun prix ne constitue une cotation ou un conseil d'investissement.")

with st.sidebar:
    st.header("Obligation à pricer")
    issuer = st.text_input("Émetteur", "OMEGA_INFRA")
    issuer_group = st.text_input("Groupe", "OMEGA")
    sector = st.selectbox("Secteur", ["Utilities", "Infrastructure", "Banking", "Transport", "Telecom"])
    currency = st.selectbox("Devise", ["EUR", "USD", "GBP"])
    rating = st.selectbox("Rating", ["AAA", "AA", "A", "BBB", "BB", "B"], index=3)
    seniority = st.selectbox("Séniorité", ["Senior", "Subordinated"])
    coupon = st.number_input("Coupon (%)", min_value=0.0, max_value=15.0, value=3.50, step=0.05)
    maturity = st.number_input("Maturité résiduelle (années)", min_value=0.5, max_value=30.0, value=5.0, step=0.5)
    callable_bond = st.checkbox("Callable", value=False)
    esg = st.checkbox("Label ESG", value=False)
    run = st.button("🚀 Lancer le pricing", type="primary", use_container_width=True)

if run:
    request = BondRequest(issuer, issuer_group, sector, currency, rating, seniority, coupon, maturity, callable_bond, esg)
    with st.spinner("LangGraph : recherche → matching → pricing → explication..."):
        result = run_pricing(request)
        try:
            save_run(request.to_dict(), result)
            st.toast("Run enregistré dans la base de données")
        except Exception as exc:
            st.info(f"Historisation indisponible : {exc}")
    st.session_state["last_result"] = result

result = st.session_state.get("last_result")
if result:
    if result.get("error"):
        st.error(result["error"])
    else:
        v = result["valuation"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix clean estimé", f"{v['clean_price']:.3f}")
        c2.metric("Spread estimé", f"{v['estimated_spread_bps']:.1f} bps")
        c3.metric("YTM estimé", f"{v['estimated_ytm_pct']:.3f} %")
        c4.metric("Confiance indicative", v["confidence"])
        st.subheader("Explication de l'agent")
        st.write(result["explanation"])
        st.caption(f"Fourchette indicative sous choc de ±25 bps : {v['price_low']:.3f} – {v['price_high']:.3f}")
        panel = v["panel_with_metrics"]
        st.subheader(f"Panel de comparables ({len(panel)})")
        display_cols = ["bond_id", "issuer", "rating", "maturity_years", "coupon_pct", "price_clean", "ytm_pct", "spread_bps", "similarity_score", "rationale"]
        st.dataframe(panel[display_cols].round(3), use_container_width=True, hide_index=True)
        fig = px.scatter(panel, x="maturity_years", y="spread_bps", size="similarity_score", color="rating", hover_name="bond_id", title="Comparables : maturité vs spread")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Renseigne les caractéristiques dans le panneau de gauche puis lance le pricing.")
    st.subheader("Parcours prototype")
    st.markdown("1. Extraction des caractéristiques  ·  2. Recherche de titres  ·  3. Ranking  ·  4. Estimation du spread  ·  5. Valorisation  ·  6. Explication")

with st.expander("Architecture et limites du prototype"):
    st.markdown("- **LangGraph** orchestre les étapes du workflow.\n- **Matching** applique des filtres structurels puis un score transparent.\n- **Pricing** estime les YTM des comparables, calcule leurs spreads et valorise les cashflows.\n- **MCP adapter** utilise actuellement un univers CSV synthétique.\n- **PostgreSQL** est disponible via Docker ; SQLite est le mode local par défaut.\n- **Mistral / RAG / vrais MCP CDC** seront intégrés après réception des documentations et accès officiels.")
