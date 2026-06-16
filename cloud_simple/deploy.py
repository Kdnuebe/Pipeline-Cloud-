"""
Déploiement AUTOMATIQUE de la version simple sur AWS (S3 + Athena + Step Functions + SNS).
Exécuté par l'assistant. Idempotent par suffixe unique. Génère des fichiers-preuves.

Usage : python cloud_simple/deploy.py --email ton@email.com [--bucket nom] [--suffix abcdef]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

import boto3
from botocore.exceptions import ClientError

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = "eu-west-3"
DB = "nyc_taxi"


def log(msg):
    print(f"  {msg}", flush=True)


# --------------------------------------------------------------------------- Athena
def athena_run(athena, output, sql, database=DB, fetch=False):
    # Athena exige toujours une base dans le contexte ; "default" existe d'office.
    ctx = {"Database": database or "default"}
    qid = athena.start_query_execution(
        QueryString=sql, QueryExecutionContext=ctx,
        ResultConfiguration={"OutputLocation": output},
    )["QueryExecutionId"]
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        if st["State"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1.5)
    if st["State"] != "SUCCEEDED":
        raise RuntimeError(f"Athena {st['State']}: {st.get('StateChangeReason','')}\n{sql[:160]}")
    if fetch:
        rows = []
        for page in athena.get_paginator("get_query_results").paginate(QueryExecutionId=qid):
            rows.extend(page["ResultSet"]["Rows"])
        if not rows:
            return []
        headers = [c.get("VarCharValue") for c in rows[0]["Data"]]
        return [dict(zip(headers, [c.get("VarCharValue") for c in r["Data"]])) for r in rows[1:]]
    return qid


def clean_prefix(s3, bucket, prefix):
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objs:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--bucket", default=None)
    ap.add_argument("--suffix", default=uuid.uuid4().hex[:6])
    args = ap.parse_args()

    suffix = args.suffix
    bucket = args.bucket or f"nyc-taxi-pipeline-{suffix}"
    athena_output = f"s3://{bucket}/athena-results/"

    sess = boto3.Session(region_name=REGION)
    s3 = sess.client("s3")
    athena = sess.client("athena")
    sns = sess.client("sns")
    iam = sess.client("iam")
    sfn = sess.client("stepfunctions")
    acct = sess.client("sts").get_caller_identity()["Account"]

    outputs = {"region": REGION, "bucket": bucket, "athena_db": DB, "suffix": suffix, "account": acct}

    # === 1. S3 bucket + chiffrement + lifecycle ============================
    print("\n[1/9] S3 : bucket, chiffrement, lifecycle")
    try:
        s3.create_bucket(Bucket=bucket,
                         CreateBucketConfiguration={"LocationConstraint": REGION})
        log(f"bucket créé : {bucket}")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            log(f"bucket déjà présent : {bucket}")
        else:
            raise
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    log("chiffrement SSE-S3 activé")
    with open(f"{ROOT}/cloud_simple/s3_lifecycle.json", encoding="utf-8") as f:
        lc = json.load(f)
    s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=lc)
    log("lifecycle (IA 30j -> Glacier 90j) configuré")

    # === 2. Upload des données =============================================
    print("\n[2/9] Upload des données vers S3")

    def upload_dir(local, prefix):
        n = 0
        for root, _, files in os.walk(local):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, local).replace("\\", "/")
                s3.upload_file(full, bucket, f"{prefix}/{rel}")
                n += 1
        return n

    log(f"bronze : {upload_dir(f'{ROOT}/data/bronze', 'bronze')} fichiers")
    log(f"ml_predictions : {upload_dir(f'{ROOT}/data/gold/ml_predictions', 'gold/ml_predictions')} fichiers")

    # === 3. Athena : base + tables bronze ==================================
    print("\n[3/9] Athena : base + tables bronze")
    athena_run(athena, athena_output, f"CREATE DATABASE IF NOT EXISTS {DB}", database=None)
    athena_run(athena, athena_output,
               f"CREATE EXTERNAL TABLE IF NOT EXISTS bronze_trips (vendorid int, "
               f"tpep_pickup_datetime timestamp, tpep_dropoff_datetime timestamp, passenger_count double, "
               f"trip_distance double, ratecodeid double, store_and_fwd_flag string, pulocationid int, "
               f"dolocationid int, payment_type bigint, fare_amount double, extra double, mta_tax double, "
               f"tip_amount double, tolls_amount double, improvement_surcharge double, total_amount double, "
               f"congestion_surcharge double, airport_fee double, driver_email string, driver_pseudo string) "
               f"STORED AS PARQUET LOCATION 's3://{bucket}/bronze/trips/'")
    athena_run(athena, athena_output,
               f"CREATE EXTERNAL TABLE IF NOT EXISTS bronze_zones (location_id bigint, borough string, "
               f"zone_name string, service_zone string) STORED AS PARQUET LOCATION 's3://{bucket}/bronze/zones/'")
    athena_run(athena, athena_output,
               f"CREATE EXTERNAL TABLE IF NOT EXISTS bronze_weather (weather_date string, "
               f"temperature_2m_mean double, temperature_2m_max double, precipitation_sum double) "
               f"STORED AS PARQUET LOCATION 's3://{bucket}/bronze/weather/'")
    nb = athena_run(athena, athena_output, "SELECT COUNT(*) n FROM bronze_trips", fetch=True)
    log(f"tables bronze créées — bronze_trips = {nb[0]['n']} lignes")

    # === 4. SNS (alerting) =================================================
    print("\n[4/9] SNS : topic d'alerte + abonnement email")
    topic_arn = sns.create_topic(Name=f"nyc-taxi-alerts-{suffix}")["TopicArn"]
    sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=args.email)
    log(f"topic {topic_arn} — CONFIRME l'email envoyé à {args.email}")
    outputs["sns_topic_arn"] = topic_arn

    # === 5. IAM : rôle pour Step Functions =================================
    print("\n[5/9] IAM : rôle Step Functions")
    role_name = f"nyc-taxi-sfn-{suffix}"
    with open(f"{ROOT}/cloud_simple/stepfunctions/iam_trust.json", encoding="utf-8") as f:
        trust = f.read()
    role_arn = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=trust)["Role"]["Arn"]
    with open(f"{ROOT}/cloud_simple/stepfunctions/iam_policy.json", encoding="utf-8") as f:
        pol = f.read().replace("VOTRE-BUCKET", bucket).replace("VOTRE_SNS_TOPIC_ARN", topic_arn)
    iam.put_role_policy(RoleName=role_name, PolicyName="perms", PolicyDocument=pol)
    log(f"rôle {role_arn} (propagation 15s…)")
    outputs["role_arn"] = role_arn
    time.sleep(15)

    # === 6. Step Functions : state machine ================================
    print("\n[6/9] Step Functions : création de la state machine")
    with open(f"{ROOT}/cloud_simple/stepfunctions/state_machine.asl.json", encoding="utf-8") as f:
        asl = f.read().replace("VOTRE-BUCKET", bucket).replace("VOTRE_SNS_TOPIC_ARN", topic_arn)
    sm_name = f"nyc-taxi-pipeline-{suffix}"
    for attempt in range(5):
        try:
            sm_arn = sfn.create_state_machine(name=sm_name, definition=asl,
                                              roleArn=role_arn, type="STANDARD")["stateMachineArn"]
            break
        except ClientError as e:
            log(f"create_state_machine retry ({e.response['Error']['Code']})…")
            time.sleep(8)
    else:
        raise RuntimeError("Impossible de créer la state machine")
    log(f"state machine : {sm_arn}")
    outputs["state_machine_arn"] = sm_arn

    # === 7. Exécuter la pipeline (Silver + Gold) ===========================
    print("\n[7/9] Step Functions : exécution (construit silver + gold via Athena)")
    # on part propre au cas où des tables existeraient déjà
    for t in ("silver_trips", "demand_by_zone_hour", "tips_analysis"):
        athena_run(athena, athena_output, f"DROP TABLE IF EXISTS {t}")
    for p in ("silver/", "gold/demand_by_zone_hour/", "gold/tips_analysis/"):
        clean_prefix(s3, bucket, p)

    exec_arn = sfn.start_execution(stateMachineArn=sm_arn)["executionArn"]
    log(f"exécution démarrée : {exec_arn}")
    while True:
        desc = sfn.describe_execution(executionArn=exec_arn)
        if desc["status"] != "RUNNING":
            break
        time.sleep(4)
    log(f"statut Step Functions : {desc['status']}")
    outputs["execution_arn"] = exec_arn
    outputs["execution_status"] = desc["status"]

    if desc["status"] != "SUCCEEDED":
        # Repli : construire silver/gold directement via Athena à partir des requêtes de l'ASL
        log("Step Functions a échoué -> repli construction directe via Athena")
        states = json.loads(asl)["States"]
        for t in ("silver_trips", "demand_by_zone_hour", "tips_analysis"):
            athena_run(athena, athena_output, f"DROP TABLE IF EXISTS {t}")
        for p in ("silver/", "gold/demand_by_zone_hour/", "gold/tips_analysis/"):
            clean_prefix(s3, bucket, p)
        for state in ("BuildSilver", "BuildGoldDemand", "BuildGoldTips"):
            athena_run(athena, athena_output, states[state]["Parameters"]["QueryString"])
        log("silver + gold construits via repli Athena")

    # === 8. Table ml_predictions + requêtes d'exploration (preuves) ========
    print("\n[8/9] Athena : table ml_predictions + requêtes métier (preuves)")
    athena_run(athena, athena_output,
               f"CREATE EXTERNAL TABLE IF NOT EXISTS ml_predictions (pickup_date string, pu_zone string, "
               f"pu_borough string, actual_total double, predicted_total double, abs_error double, "
               f"is_anomaly bigint) STORED AS PARQUET LOCATION 's3://{bucket}/gold/ml_predictions/'")
    proofs = {
        "top_zones": "SELECT pu_borough, pu_zone, SUM(trips) trips, ROUND(SUM(revenue_total),0) revenu "
                     "FROM demand_by_zone_hour GROUP BY 1,2 ORDER BY revenu DESC LIMIT 10",
        "heures_actives": "SELECT pickup_hour, SUM(trips) courses FROM demand_by_zone_hour "
                          "GROUP BY 1 ORDER BY courses DESC LIMIT 5",
        "pourboires_paiement": "SELECT payment_type, ROUND(AVG(avg_tip_pct),1) tip_pct, SUM(trips) courses "
                               "FROM tips_analysis GROUP BY 1 ORDER BY courses DESC",
        "anomalies": "SELECT pu_borough, pu_zone, actual_total, predicted_total, abs_error "
                     "FROM ml_predictions WHERE is_anomaly=1 ORDER BY abs_error DESC LIMIT 10",
    }
    os.makedirs(f"{ROOT}/cloud_simple/proof", exist_ok=True)
    for name, sql in proofs.items():
        res = athena_run(athena, athena_output, sql, fetch=True)
        with open(f"{ROOT}/cloud_simple/proof/{name}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        log(f"{name}: {len(res)} lignes -> cloud_simple/proof/{name}.json")

    # === 9. Budget d'alerte de coût =======================================
    print("\n[9/9] AWS Budgets : alerte coût 5 USD")
    try:
        budgets = sess.client("budgets", region_name="us-east-1")
        budgets.create_budget(
            AccountId=acct,
            Budget={"BudgetName": f"nyc-taxi-budget-{suffix}",
                    "BudgetLimit": {"Amount": "5", "Unit": "USD"},
                    "TimeUnit": "MONTHLY", "BudgetType": "COST"},
            NotificationsWithSubscribers=[{
                "Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN",
                                 "Threshold": 80.0, "ThresholdType": "PERCENTAGE"},
                "Subscribers": [{"SubscriptionType": "EMAIL", "Address": args.email}],
            }],
        )
        log("budget 5 USD créé (alerte email à 80%)")
        outputs["budget"] = f"nyc-taxi-budget-{suffix}"
    except Exception as e:
        log(f"budget non créé (non bloquant) : {e}")

    # === Sauvegarde des sorties ===========================================
    with open(f"{ROOT}/cloud_simple/deploy_outputs.json", "w", encoding="utf-8") as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)
    print("\n==================== DÉPLOIEMENT TERMINÉ ====================")
    print(json.dumps(outputs, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
