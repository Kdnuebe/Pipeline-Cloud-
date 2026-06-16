"""
COUCHE GOLD — API REST (FastAPI) exposant les datamarts.

Documentation Swagger/OpenAPI auto-générée sur http://localhost:8000/docs
Lancement local :  uvicorn api.app:app --reload

Lecture des datamarts gold en local via DuckDB (sur les Parquet de ./data/gold).
Sur AWS, c'est api/lambda_handler.py (mêmes endpoints, requêtes Athena) qui est déployé.
"""
from __future__ import annotations

import os

import duckdb
from fastapi import FastAPI, Query

DATA_ROOT = os.environ.get("DATA_ROOT", "./data").rstrip("/")
GOLD = f"{DATA_ROOT}/gold"

app = FastAPI(
    title="NYC Taxi — API Datamarts Gold",
    version="1.0.0",
    description="Endpoints métier exposant les datamarts (demande, pourboires, prédictions ML). "
    "Architecture médaillon Bronze→Silver→Gold sur AWS.",
)


def q(sql: str) -> list[dict]:
    """Exécute une requête DuckDB sur les Parquet gold et renvoie une liste de dicts."""
    con = duckdb.connect()
    try:
        return con.execute(sql).df().to_dict(orient="records")
    finally:
        con.close()


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "NYC Taxi Gold API",
        "endpoints": ["/health", "/zones/top", "/demand", "/tips", "/predictions", "/ml/metrics"],
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/zones/top", tags=["demande"])
def top_zones(limit: int = Query(10, ge=1, le=100)):
    """Top des zones de prise en charge par revenu total (problématique #1)."""
    return q(
        f"""
        SELECT pu_borough, pu_zone,
               SUM(trips) AS trips,
               ROUND(SUM(revenue_total), 2) AS revenue_total
        FROM read_parquet('{GOLD}/demand_by_zone_hour/*.parquet')
        GROUP BY pu_borough, pu_zone
        ORDER BY revenue_total DESC
        LIMIT {int(limit)}
        """
    )


@app.get("/demand", tags=["demande"])
def demand(
    borough: str | None = Query(None, description="Filtrer par arrondissement"),
    hour: int | None = Query(None, ge=0, le=23, description="Filtrer par heure (0-23)"),
    limit: int = Query(50, ge=1, le=500),
):
    """Demande par zone × heure × jour (problématique #1)."""
    where = []
    if borough:
        where.append(f"pu_borough = '{borough.replace(chr(39), chr(39)*2)}'")
    if hour is not None:
        where.append(f"pickup_hour = {int(hour)}")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    return q(
        f"""
        SELECT pu_borough, pu_zone, pickup_hour, pickup_dow_iso,
               trips, revenue_total, avg_ticket, avg_distance_mi, avg_duration_min
        FROM read_parquet('{GOLD}/demand_by_zone_hour/*.parquet')
        {clause}
        ORDER BY trips DESC
        LIMIT {int(limit)}
        """
    )


@app.get("/tips", tags=["pourboires"])
def tips():
    """Analyse des pourboires par arrondissement / paiement / heure / météo (problématique #2)."""
    return q(
        f"""
        SELECT pu_borough, payment_type, is_rush_hour, is_rainy,
               trips, avg_tip_pct, avg_tip_amount, avg_ticket
        FROM read_parquet('{GOLD}/tips_analysis/*.parquet')
        ORDER BY avg_tip_pct DESC
        """
    )


@app.get("/predictions", tags=["ml"])
def predictions(limit: int = Query(100, ge=1, le=1000), anomalies_only: bool = False):
    """Prédictions ML (réel vs prédit) + anomalies, exposées en gold (problématique #3)."""
    clause = "WHERE is_anomaly = 1" if anomalies_only else ""
    return q(
        f"""
        SELECT pickup_date, pu_borough, pu_zone,
               actual_total, predicted_total, abs_error, is_anomaly
        FROM read_parquet('{GOLD}/ml_predictions/*.parquet')
        {clause}
        ORDER BY abs_error DESC
        LIMIT {int(limit)}
        """
    )


@app.get("/ml/metrics", tags=["ml"])
def ml_metrics():
    """Métriques du modèle ML comparées à la baseline."""
    import json

    path = f"{GOLD}/ml_metrics/metrics.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"error": "métriques non disponibles — lancer la pipeline ML d'abord"}
