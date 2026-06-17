"""
DESTRUCTION de toutes les ressources AWS créées par deploy.py (arrête les coûts).
Lit cloud_simple/deploy_outputs.json. Lancer : python cloud_simple/teardown.py
"""
from __future__ import annotations

import json
import os
import sys

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with open(f"{ROOT}/cloud_simple/deploy_outputs.json", encoding="utf-8") as f:
        o = json.load(f)
    sess = boto3.Session(region_name=o["region"])
    suffix = o["suffix"]

    def safe(label, fn):
        try:
            fn()
            print(f"  supprimé : {label}")
        except Exception as e:  # noqa: BLE001
            print(f"  (déjà absent / ignoré) {label} : {e}")

    print("Destruction des ressources AWS…")
    safe("state machine", lambda: sess.client("stepfunctions").delete_state_machine(
        stateMachineArn=o["state_machine_arn"]))
    iam = sess.client("iam")
    safe("IAM policy", lambda: iam.delete_role_policy(
        RoleName=f"nyc-taxi-sfn-{suffix}", PolicyName="perms"))
    safe("IAM role", lambda: iam.delete_role(RoleName=f"nyc-taxi-sfn-{suffix}"))
    safe("SNS topic", lambda: sess.client("sns").delete_topic(TopicArn=o["sns_topic_arn"]))
    if o.get("budget"):
        safe("budget", lambda: sess.client("budgets", region_name="us-east-1").delete_budget(
            AccountId=o["account"], BudgetName=o["budget"]))

    # Vider puis supprimer le bucket
    s3 = sess.resource("s3")
    bucket = s3.Bucket(o["bucket"])
    safe("contenu du bucket", lambda: bucket.objects.all().delete())
    safe("bucket", lambda: bucket.delete())
    print("Terminé. Vérifie dans la console que tout a disparu (coût stoppé).")


if __name__ == "__main__":
    main()
