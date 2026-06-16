"""
JOB GLUE (Python Shell) — Étapes SILVER + GOLD sur AWS, via ATHENA (CTAS).

Exécute exactement le MÊME SQL que la version locale DuckDB (téléchargé depuis le
bucket d'artefacts), avec une seule différence : le jeton __DOW__ remplacé par
l'expression Athena/Trino.

Pré-requis : le crawler Glue a déjà catalogué les tables bronze_trips / bronze_zones
/ bronze_weather (tâche précédente de la state machine).

Pour chaque table cible : DROP table + vidage de l'emplacement S3 + CREATE TABLE AS.
"""
import sys
import time

import boto3
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(
    sys.argv,
    ["DATA_LAKE_BUCKET", "ARTIFACTS_BUCKET", "ATHENA_DB", "ATHENA_OUTPUT", "AWS_REGION"],
)
BUCKET = args["DATA_LAKE_BUCKET"]
ARTIFACTS = args["ARTIFACTS_BUCKET"]
DB = args["ATHENA_DB"]
OUTPUT = args["ATHENA_OUTPUT"]
REGION = args["AWS_REGION"]

# Athena/Trino : EXTRACT(DOW ...) renvoie 1=Lundi..7=Dimanche (norme ISO, comme DuckDB isodow)
ATHENA_DOW = "EXTRACT(DOW FROM t.tpep_pickup_datetime)"

athena = boto3.client("athena", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


def get_sql(key: str) -> str:
    body = s3.get_object(Bucket=ARTIFACTS, Key="sql/" + key)["Body"].read().decode("utf-8")
    return body.replace("__DOW__", ATHENA_DOW)


def run(query: str) -> None:
    qid = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": DB},
        ResultConfiguration={"OutputLocation": OUTPUT},
    )["QueryExecutionId"]
    while True:
        info = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        state = info["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena {state}: {info.get('StateChangeReason','')}\n{query[:300]}")
    print(f"[athena] OK : {query.splitlines()[0][:80]}", flush=True)


def clean_prefix(prefix: str) -> None:
    """Vide un préfixe S3 (CTAS exige un emplacement vide)."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objs:
            s3.delete_objects(Bucket=BUCKET, Delete={"Objects": objs})


def ctas(table: str, sql_key: str, location_prefix: str) -> None:
    run(f"DROP TABLE IF EXISTS {table}")
    clean_prefix(location_prefix)
    select = get_sql(sql_key)
    run(
        f"CREATE TABLE {table} WITH (format='PARQUET', "
        f"external_location='s3://{BUCKET}/{location_prefix}') AS ({select})"
    )


# --- SILVER -----------------------------------------------------------------
ctas("silver_trips", "silver_trips.sql", "silver/trips/")
# --- GOLD -------------------------------------------------------------------
ctas("demand_by_zone_hour", "gold_demand_by_zone_hour.sql", "gold/demand_by_zone_hour/")
ctas("tips_analysis", "gold_tips_analysis.sql", "gold/tips_analysis/")
print("[transform] Silver + Gold construits via Athena.", flush=True)
