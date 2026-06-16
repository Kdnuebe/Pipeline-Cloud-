"""
COUCHE GOLD — API REST sur AWS (Lambda + API Gateway HTTP API).

Mêmes endpoints que api/app.py (FastAPI local), mais en lecture sur ATHENA via boto3
(aucune dépendance externe -> zip Lambda léger, pas de conteneur Docker).

Variables d'environnement (fournies par Terraform) :
  ATHENA_DB, ATHENA_OUTPUT, DATA_LAKE_BUCKET, AWS_REGION
"""
import json
import os
import time

import boto3

DB = os.environ["ATHENA_DB"]
OUTPUT = os.environ["ATHENA_OUTPUT"]
BUCKET = os.environ["DATA_LAKE_BUCKET"]
REGION = os.environ.get("AWS_REGION", "eu-west-3")

athena = boto3.client("athena", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


def query(sql: str) -> list[dict]:
    qid = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DB},
        ResultConfiguration={"OutputLocation": OUTPUT},
    )["QueryExecutionId"]
    while True:
        state = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena {state}")
    res = athena.get_query_results(QueryExecutionId=qid)
    rows = res["ResultSet"]["Rows"]
    headers = [c["VarCharValue"] for c in rows[0]["Data"]]
    out = []
    for r in rows[1:]:
        vals = [c.get("VarCharValue") for c in r["Data"]]
        out.append(dict(zip(headers, vals)))
    return out


def reply(status: int, body) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }


def handler(event, context):
    path = event.get("rawPath") or event.get("path") or "/"
    qs = event.get("queryStringParameters") or {}
    try:
        if path in ("/", ""):
            return reply(200, {"service": "NYC Taxi Gold API",
                               "endpoints": ["/health", "/zones/top", "/demand", "/tips",
                                             "/predictions", "/ml/metrics"]})
        if path == "/health":
            return reply(200, {"status": "ok"})

        if path == "/zones/top":
            limit = int(qs.get("limit", 10))
            return reply(200, query(
                f"SELECT pu_borough, pu_zone, SUM(trips) trips, "
                f"ROUND(SUM(revenue_total),2) revenue_total "
                f"FROM demand_by_zone_hour GROUP BY pu_borough, pu_zone "
                f"ORDER BY revenue_total DESC LIMIT {limit}"))

        if path == "/demand":
            conds = []
            if qs.get("borough"):
                conds.append("pu_borough = '" + qs["borough"].replace("'", "''") + "'")
            if qs.get("hour"):
                conds.append(f"pickup_hour = {int(qs['hour'])}")
            where = ("WHERE " + " AND ".join(conds)) if conds else ""
            limit = int(qs.get("limit", 50))
            return reply(200, query(
                f"SELECT pu_borough, pu_zone, pickup_hour, pickup_dow_iso, trips, "
                f"revenue_total, avg_ticket, avg_distance_mi, avg_duration_min "
                f"FROM demand_by_zone_hour {where} ORDER BY trips DESC LIMIT {limit}"))

        if path == "/tips":
            return reply(200, query(
                "SELECT pu_borough, payment_type, is_rush_hour, is_rainy, trips, "
                "avg_tip_pct, avg_tip_amount, avg_ticket FROM tips_analysis "
                "ORDER BY avg_tip_pct DESC"))

        if path == "/predictions":
            limit = int(qs.get("limit", 100))
            where = "WHERE is_anomaly = 1" if qs.get("anomalies_only") == "true" else ""
            return reply(200, query(
                f"SELECT pickup_date, pu_borough, pu_zone, actual_total, predicted_total, "
                f"abs_error, is_anomaly FROM ml_predictions {where} "
                f"ORDER BY abs_error DESC LIMIT {limit}"))

        if path == "/ml/metrics":
            obj = s3.get_object(Bucket=BUCKET, Key="gold/ml_metrics/metrics.json")
            return reply(200, json.loads(obj["Body"].read()))

        return reply(404, {"error": "not found", "path": path})
    except Exception as exc:  # noqa: BLE001
        return reply(500, {"error": str(exc)})
