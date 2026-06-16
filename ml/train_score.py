"""
BONUS ML — intégré DANS la pipeline (tâche dédiée, pas un notebook isolé).

Deux modèles, entraînés sur la couche silver, prédictions écrites en couche GOLD :
  1. Régression  : prédire le montant total d'une course (total_amount)
  2. Anomalies   : IsolationForest pour repérer les courses tarifaires atypiques

Métriques comparées à une BASELINE simple (prédire la moyenne).
Sorties gold :
  - gold/ml_predictions/predictions.parquet  (réel vs prédit + drapeau anomalie)
  - gold/ml_metrics/metrics.json             (métriques + importances de variables)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline_common import DATA_ROOT, log, put_metric, read_parquet_dataset, write_parquet  # noqa: E402

FEATURES = [
    "trip_distance", "passenger_count", "pickup_hour", "pickup_dow_iso",
    "is_weekend", "is_rush_hour", "pu_location_id", "do_location_id",
    "temp_mean_c", "precip_mm",
]
TARGET = "total_amount"
SAMPLE_ROWS = int(os.environ.get("ML_SAMPLE_ROWS", "200000"))


def main() -> None:
    log("=== ML — entraînement & scoring ===")
    df = read_parquet_dataset(f"{DATA_ROOT}/silver/trips")

    # Échantillonnage pour rester rapide et gratuit
    if len(df) > SAMPLE_ROWS:
        df = df.sample(SAMPLE_ROWS, random_state=42)
    log(f"[ml] {len(df):,} lignes utilisées (échantillon)")

    # Préparation : bool -> int, remplissage météo manquante, suppression des NaN cibles
    work = df.copy()
    for c in ["is_weekend", "is_rush_hour"]:
        work[c] = work[c].astype(int)
    for c in ["temp_mean_c", "precip_mm"]:
        work[c] = work[c].fillna(work[c].median())
    work = work.dropna(subset=FEATURES + [TARGET])

    X, y = work[FEATURES], work[TARGET]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- BASELINE : prédire la moyenne ------------------------------------
    baseline_pred = np.full(len(y_te), y_tr.mean())
    base_mae = mean_absolute_error(y_te, baseline_pred)
    base_rmse = float(np.sqrt(mean_squared_error(y_te, baseline_pred)))

    # --- MODÈLE : RandomForest --------------------------------------------
    model = RandomForestRegressor(
        n_estimators=60, max_depth=14, n_jobs=-1, random_state=42
    )
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    mae = mean_absolute_error(y_te, pred)
    rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
    r2 = r2_score(y_te, pred)
    log(f"[ml] Baseline   MAE={base_mae:.3f}  RMSE={base_rmse:.3f}")
    log(f"[ml] RandomForest MAE={mae:.3f}  RMSE={rmse:.3f}  R2={r2:.3f}")
    log(f"[ml] Gain MAE vs baseline : {(1 - mae / base_mae) * 100:.1f}%")

    # --- ANOMALIES : IsolationForest --------------------------------------
    iso = IsolationForest(contamination=0.02, random_state=42, n_estimators=100)
    iso_features = ["trip_distance", "trip_duration_min", "total_amount", "tip_amount"]
    iso_in = work.loc[X_te.index, iso_features].fillna(0)
    anomaly = (iso.fit_predict(iso_in) == -1).astype(int)

    # --- Écriture des prédictions en GOLD ---------------------------------
    out = work.loc[X_te.index, ["pickup_date", "pu_zone", "pu_borough", TARGET]].copy()
    out = out.rename(columns={TARGET: "actual_total"})
    out["pickup_date"] = out["pickup_date"].astype(str)  # type non ambigu (string) local & Athena
    out["predicted_total"] = np.round(pred, 2)
    out["abs_error"] = np.round(np.abs(out["actual_total"] - out["predicted_total"]), 2)
    out["is_anomaly"] = anomaly
    out = out.head(10000)  # échantillon exposé
    write_parquet(out, f"{DATA_ROOT}/gold/ml_predictions/predictions.parquet")
    log(f"[ml] {len(out):,} prédictions écrites -> gold/ml_predictions/")

    # --- Versionnement du modèle : sauvegarde de l'artefact horodaté ------
    run_id = pd.Timestamp.now("UTC").strftime("%Y%m%dT%H%M%SZ")
    if not f"{DATA_ROOT}".startswith("s3://"):
        import joblib

        os.makedirs(f"{DATA_ROOT}/models", exist_ok=True)
        joblib.dump(model, f"{DATA_ROOT}/models/model_{run_id}.pkl")
        joblib.dump(model, f"{DATA_ROOT}/models/model_latest.pkl")
        log(f"[ml] Modèle versionné -> models/model_{run_id}.pkl")

    # --- Métriques + importances (versionnement léger) --------------------
    metrics = {
        "run_id": run_id,
        "model": "RandomForestRegressor",
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "baseline": {"mae": round(base_mae, 4), "rmse": round(base_rmse, 4)},
        "model_metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)},
        "improvement_mae_pct": round((1 - mae / base_mae) * 100, 2),
        "feature_importance": {
            f: round(float(i), 4)
            for f, i in sorted(
                zip(FEATURES, model.feature_importances_), key=lambda kv: -kv[1]
            )
        },
        "anomalies_detected": int(anomaly.sum()),
    }
    os.makedirs(f"{DATA_ROOT}/gold/ml_metrics", exist_ok=True)
    # metrics.json : écrit en local en clair (et lisible en S3 via le même chemin)
    if not f"{DATA_ROOT}".startswith("s3://"):
        with open(f"{DATA_ROOT}/gold/ml_metrics/metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
    else:
        import boto3
        from pipeline_common import _split_s3  # type: ignore

        bucket, key = _split_s3(f"{DATA_ROOT}/gold/ml_metrics/metrics.json")
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=json.dumps(metrics, indent=2))

    put_metric("MLModelMAE", mae)
    put_metric("MLImprovementPct", metrics["improvement_mae_pct"])
    log("=== ML terminé ===")


if __name__ == "__main__":
    main()
