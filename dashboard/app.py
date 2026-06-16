"""
COUCHE GOLD — Dashboard interactif (Streamlit + Plotly).

Lancement local :  streamlit run dashboard/app.py
Lit les datamarts gold (Parquet sous ./data/gold) via DuckDB.

Répond visuellement aux 3 problématiques métier :
  1. Demande & revenus par zone/heure   2. Pourboires   3. Prédictions ML
"""
from __future__ import annotations

import json
import os

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DATA_ROOT = os.environ.get("DATA_ROOT", "./data").rstrip("/")
GOLD = f"{DATA_ROOT}/gold"
DOW = {1: "Lun", 2: "Mar", 3: "Mer", 4: "Jeu", 5: "Ven", 6: "Sam", 7: "Dim"}

st.set_page_config(page_title="NYC Taxi — Datamarts Gold", layout="wide")


@st.cache_data
def load(table: str) -> pd.DataFrame:
    return duckdb.connect().execute(
        f"SELECT * FROM read_parquet('{GOLD}/{table}/*.parquet')"
    ).df()


st.title("🚕 NYC Yellow Taxi — Pipeline Médaillon (couche Gold)")
st.caption("Architecture Bronze → Silver → Gold · AWS · Master 2 Data Engineering & IA")

try:
    demand = load("demand_by_zone_hour")
    tips = load("tips_analysis")
    preds = load("ml_predictions")
except Exception:
    st.error("Aucune donnée gold trouvée. Lance d'abord :  python run_local_pipeline.py 2024-01")
    st.stop()

# ----------------------------- KPIs ----------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Courses (mailles k≥5)", f"{int(demand['trips'].sum()):,}")
c2.metric("Revenu total", f"${demand['revenue_total'].sum():,.0f}")
c3.metric("Ticket moyen", f"${demand['avg_ticket'].mean():.2f}")
c4.metric("Zones couvertes", f"{demand['pu_zone'].nunique()}")

tab1, tab2, tab3 = st.tabs(["📍 Demande & revenus", "💸 Pourboires", "🤖 Prédictions ML"])

# ----------------------- Problématique 1 -----------------------------------
with tab1:
    st.subheader("Top 15 zones par revenu")
    top = (
        demand.groupby(["pu_borough", "pu_zone"], as_index=False)["revenue_total"].sum()
        .sort_values("revenue_total", ascending=False).head(15)
    )
    st.plotly_chart(
        px.bar(top, x="revenue_total", y="pu_zone", color="pu_borough", orientation="h"),
        use_container_width=True,
    )

    st.subheader("Heatmap de la demande : heure × jour de semaine")
    heat = demand.groupby(["pickup_dow_iso", "pickup_hour"], as_index=False)["trips"].sum()
    heat["jour"] = heat["pickup_dow_iso"].map(DOW)
    pivot = heat.pivot(index="jour", columns="pickup_hour", values="trips").reindex(
        ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    )
    st.plotly_chart(px.imshow(pivot, aspect="auto", labels={"color": "courses"}),
                    use_container_width=True)

# ----------------------- Problématique 2 -----------------------------------
with tab2:
    st.subheader("Taux de pourboire moyen par arrondissement & mode de paiement")
    pay = {1: "Carte", 2: "Espèces", 3: "Gratuit", 4: "Litige", 5: "Inconnu"}
    t = tips.copy()
    t["paiement"] = t["payment_type"].map(pay).fillna("Autre")
    st.plotly_chart(
        px.bar(t, x="pu_borough", y="avg_tip_pct", color="paiement", barmode="group"),
        use_container_width=True,
    )
    st.info("💡 Les pourboires par carte sont enregistrés (≈25-30 %), pas ceux en espèces (≈0 %).")
    st.dataframe(t, use_container_width=True)

# ----------------------- Problématique 3 (ML) ------------------------------
with tab3:
    metrics_path = f"{GOLD}/ml_metrics/metrics.json"
    if os.path.exists(metrics_path):
        m = json.load(open(metrics_path, encoding="utf-8"))
        k1, k2, k3 = st.columns(3)
        k1.metric("R² du modèle", f"{m['model_metrics']['r2']:.3f}")
        k2.metric("MAE modèle", f"${m['model_metrics']['mae']:.2f}",
                  delta=f"-{m['improvement_mae_pct']:.0f}% vs baseline")
        k3.metric("Anomalies détectées", f"{m['anomalies_detected']}")
        st.subheader("Importance des variables")
        fi = pd.DataFrame(m["feature_importance"].items(), columns=["variable", "importance"])
        st.plotly_chart(px.bar(fi, x="importance", y="variable", orientation="h"),
                        use_container_width=True)

    st.subheader("Réel vs Prédit (montant des courses)")
    fig = px.scatter(preds, x="actual_total", y="predicted_total", color="is_anomaly",
                     color_continuous_scale=["#2986cc", "#cc0000"], opacity=0.5)
    fig.add_shape(type="line", x0=0, y0=0, x1=preds["actual_total"].max(),
                  y1=preds["actual_total"].max(), line=dict(dash="dash"))
    st.plotly_chart(fig, use_container_width=True)
