"""
JOB GLUE (Python Shell) — Étape QUALITÉ sur AWS.
Réutilise quality/checks.py (uploadé via --extra-py-files). Sort en erreur si un
test critique échoue -> Step Functions déclenche l'alerte SNS.
"""
import os
import sys

from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["DATA_LAKE_BUCKET", "AWS_REGION"])
os.environ["DATA_ROOT"] = "s3://" + args["DATA_LAKE_BUCKET"]
os.environ["AWS_REGION"] = args["AWS_REGION"]

import checks  # noqa: E402

checks.main()
