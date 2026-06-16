"""
COUCHE BRONZE — Ingestion brute (aucune transformation métier).

Ce script télécharge les 3 sources et les dépose au format Parquet, partitionné,
dans le "data lake" (dossier local en dev, bucket S3 sur AWS).

Sources :
  1. NYC TLC Yellow Taxi  -> ~3M lignes/mois, Parquet officiel
  2. Taxi Zone Lookup     -> table de référence LocationID -> Borough/Zone
  3. Météo (Open-Meteo)   -> température + précipitations par jour (API gratuite)

Particularité RGPD : les données TLC ne contiennent plus de PII directe (GPS retirés).
Pour DÉMONTRER la pseudonymisation, on ajoute un champ SYNTHÉTIQUE `driver_email`
(identifiant personnel fictif) ET sa version pseudonymisée `driver_pseudo` (haché).
La couche silver ne gardera que `driver_pseudo` (voir transformations/sql/silver_trips.sql).

Usage local :
    python data_ingestion/ingest.py                 # mois lus depuis .env (TLC_MONTHS)
    python data_ingestion/ingest.py 2024-01 2024-02 # mois passés en argument
"""
from __future__ import annotations

import hashlib
import io
import os
import sys
from datetime import date, timedelta

import pandas as pd
import requests

# Permet d'importer les helpers communs (storage local OU s3://)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline_common import (  # noqa: E402
    DATA_ROOT,
    PSEUDO_SALT,
    get_months,
    log,
    put_metric,
    write_parquet,
)

TLC_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet"
ZONES_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# Coordonnées de New York City (pour la météo)
NYC_LAT, NYC_LON = 40.7128, -74.0060

# Pool de chauffeurs synthétiques (pour la démonstration RGPD uniquement)
N_SYNTHETIC_DRIVERS = 5000


def pseudonymize(value: str) -> str:
    """Pseudonymisation = hachage SHA-256 salé (irréversible sans le sel)."""
    return hashlib.sha256((PSEUDO_SALT + value).encode("utf-8")).hexdigest()[:16]


def ingest_trips(month: str) -> int:
    """Télécharge un mois de courses, ajoute les champs RGPD synthétiques, écrit en bronze."""
    year, mm = month.split("-")
    url = TLC_URL.format(month=month)
    log(f"[bronze] Téléchargement courses {month} : {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    df = pd.read_parquet(io.BytesIO(resp.content))

    # --- Champs SYNTHÉTIQUES pour la démonstration RGPD (cf. docstring) ---
    rng = pd.Series(range(len(df)))
    driver_ids = (rng * 2654435761 % N_SYNTHETIC_DRIVERS)  # affectation déterministe
    df["driver_email"] = "driver" + driver_ids.astype(str) + "@taxi.nyc"   # PII fictive (clair)
    df["driver_pseudo"] = df["driver_email"].map(pseudonymize)             # version protégée

    # Traçabilité de l'ingestion (métadonnées)
    df["_ingested_at"] = pd.Timestamp.now("UTC")
    df["_source_file"] = f"yellow_tripdata_{month}.parquet"

    out = f"{DATA_ROOT}/bronze/trips/year={year}/month={mm}/data.parquet"
    write_parquet(df, out)
    log(f"[bronze] {len(df):,} lignes écrites -> {out}")
    put_metric("RowsIngested", len(df), dims={"layer": "bronze", "month": month})
    return len(df)


def ingest_zones() -> int:
    """Table de référence des zones (petite, change rarement -> full load)."""
    log(f"[bronze] Téléchargement zones : {ZONES_URL}")
    df = pd.read_csv(ZONES_URL)
    # Normalisation légère des noms de colonnes (évite les mots réservés SQL "Zone"
    # et les soucis de casse entre DuckDB et Athena).
    df = df.rename(
        columns={
            "LocationID": "location_id",
            "Borough": "borough",
            "Zone": "zone_name",
            "service_zone": "service_zone",
        }
    )
    out = f"{DATA_ROOT}/bronze/zones/zones.parquet"
    write_parquet(df, out)
    log(f"[bronze] {len(df):,} zones écrites -> {out}")
    return len(df)


def ingest_weather(month: str) -> int:
    """Météo quotidienne NYC pour le mois (jointure par date en silver)."""
    year, mm = month.split("-")
    start = date(int(year), int(mm), 1)
    # dernier jour du mois
    nxt = date(start.year + (start.month == 12), (start.month % 12) + 1, 1)
    end = nxt - timedelta(days=1)
    params = {
        "latitude": NYC_LAT,
        "longitude": NYC_LON,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,temperature_2m_max,precipitation_sum",
        "timezone": "America/New_York",
    }
    log(f"[bronze] Téléchargement météo {month}")
    resp = requests.get(METEO_URL, params=params, timeout=60)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    df = pd.DataFrame(daily).rename(columns={"time": "weather_date"})
    out = f"{DATA_ROOT}/bronze/weather/year={year}/month={mm}/weather.parquet"
    write_parquet(df, out)
    log(f"[bronze] {len(df):,} jours météo écrits -> {out}")
    return len(df)


def main(months: list[str]) -> None:
    log(f"=== INGESTION BRONZE — mois : {months} ===")
    total = 0
    for m in months:
        total += ingest_trips(m)
        ingest_weather(m)
    ingest_zones()
    log(f"=== BRONZE terminé : {total:,} courses au total ===")


if __name__ == "__main__":
    cli_months = sys.argv[1:] if len(sys.argv) > 1 else get_months()
    main(cli_months)
