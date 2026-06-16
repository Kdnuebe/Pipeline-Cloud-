"""
JOB GLUE (Python Shell) — Étape ML sur AWS (bonus).

1) Réutilise ml/train_score.py (uploadé via --extra-py-files) : entraîne, score,
   écrit prédictions + métriques en couche gold (S3).
2) Catalogue la table Athena `ml_predictions` pour que l'API/dashboard puissent la lire.
"""
import os
import sys
import time

import boto3
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(
    sys.argv,
    ["DATA_LAKE_BUCKET", "AWS_REGION", "ML_SAMPLE_ROWS", "ATHENA_DB", "ATHENA_OUTPUT"],
)
BUCKET = args["DATA_LAKE_BUCKET"]
REGION = args["AWS_REGION"]
DB = args["ATHENA_DB"]
OUTPUT = args["ATHENA_OUTPUT"]

os.environ["DATA_ROOT"] = "s3://" + BUCKET
os.environ["AWS_REGION"] = REGION
os.environ["ML_SAMPLE_ROWS"] = args["ML_SAMPLE_ROWS"]

import train_score  # noqa: E402

train_score.main()

# --- Catalogue Athena pour la table de prédictions -------------------------
athena = boto3.client("athena", region_name=REGION)
ddl = f"""
CREATE EXTERNAL TABLE IF NOT EXISTS ml_predictions (
  pickup_date string, pu_zone string, pu_borough string,
  actual_total double, predicted_total double, abs_error double, is_anomaly bigint
)
STORED AS PARQUET
LOCATION 's3://{BUCKET}/gold/ml_predictions/'
"""
qid = athena.start_query_execution(
    QueryString=ddl,
    QueryExecutionContext={"Database": DB},
    ResultConfiguration={"OutputLocation": OUTPUT},
)["QueryExecutionId"]
while True:
    state = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
    if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
        break
    time.sleep(1)
print(f"[ml] catalogage ml_predictions: {state}", flush=True)
