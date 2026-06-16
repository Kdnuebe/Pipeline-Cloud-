"""
Helpers partagés par les scripts de la pipeline.

Objectif : le MÊME code fonctionne en local (dossier ./data) et sur AWS (s3://...).
Le comportement bascule selon que DATA_ROOT commence par "s3://" ou non.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd

# Force l'UTF-8 sur la sortie console (sinon Windows/cp1252 plante sur les accents/emojis)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# Charge le fichier .env s'il existe (pratique en local)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv non installé : pas grave
    pass

# --- Configuration lue depuis l'environnement -----------------------------
DATA_ROOT = os.environ.get("DATA_ROOT", "./data").rstrip("/")
PSEUDO_SALT = os.environ.get("PSEUDO_SALT", "change-me-please")
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-3")
METRIC_NAMESPACE = "TaxiPipeline"

IS_CLOUD = DATA_ROOT.startswith("s3://")


def log(msg: str) -> None:
    """Log horodaté (visible dans la console locale ET dans CloudWatch Logs)."""
    print(f"{datetime.utcnow().isoformat(timespec='seconds')}Z | {msg}", flush=True)


def get_months() -> list[str]:
    """Liste des mois à ingérer, depuis la variable TLC_MONTHS (ex: '2024-01,2024-02')."""
    raw = os.environ.get("TLC_MONTHS", "2024-01")
    return [m.strip() for m in raw.split(",") if m.strip()]


def _split_s3(path: str) -> tuple[str, str]:
    """'s3://bucket/a/b.parquet' -> ('bucket', 'a/b.parquet')."""
    no_scheme = path[len("s3://"):]
    bucket, _, key = no_scheme.partition("/")
    return bucket, key


def write_parquet(df: pd.DataFrame, path: str) -> None:
    """Écrit un DataFrame en Parquet, en local OU sur S3 (selon le préfixe du chemin)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pandas(df, preserve_index=False)
    if path.startswith("s3://"):
        import pyarrow.fs as pafs

        bucket, key = _split_s3(path)
        fs = pafs.S3FileSystem(region=AWS_REGION)
        pq.write_table(table, f"{bucket}/{key}", filesystem=fs)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pq.write_table(table, path)


def read_parquet_dataset(path: str) -> pd.DataFrame:
    """Lit un dossier Parquet (récursivement) en local OU sur S3 -> DataFrame pandas."""
    import pyarrow.dataset as ds

    if path.startswith("s3://"):
        import pyarrow.fs as pafs

        bucket, key = _split_s3(path)
        fs = pafs.S3FileSystem(region=AWS_REGION)
        dataset = ds.dataset(f"{bucket}/{key}", filesystem=fs, format="parquet")
    else:
        dataset = ds.dataset(path, format="parquet")
    return dataset.to_table().to_pandas()


def put_metric(name: str, value: float, dims: dict | None = None) -> None:
    """Publie une métrique CloudWatch sur AWS ; en local, se contente de logger."""
    if not IS_CLOUD:
        log(f"[metric] {name}={value} {dims or ''}")
        return
    try:
        import boto3

        cw = boto3.client("cloudwatch", region_name=AWS_REGION)
        dimensions = [{"Name": k, "Value": str(v)} for k, v in (dims or {}).items()]
        cw.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[{"MetricName": name, "Value": float(value), "Dimensions": dimensions}],
        )
    except Exception as exc:  # ne jamais faire échouer la pipeline pour une métrique
        log(f"[metric] échec publication {name}: {exc}")
