"""
JOB GLUE (Python Shell) — Étape BRONZE sur AWS.

Lanceur fin : configure l'environnement (DATA_ROOT = s3://bucket) puis appelle la
MÊME logique d'ingestion que celle validée en local (data_ingestion/ingest.py,
uploadée via --extra-py-files par Terraform).
"""
import os
import sys

from awsglue.utils import getResolvedOptions

args = getResolvedOptions(
    sys.argv, ["DATA_LAKE_BUCKET", "AWS_REGION", "TLC_MONTHS", "PSEUDO_SALT"]
)
os.environ["DATA_ROOT"] = "s3://" + args["DATA_LAKE_BUCKET"]
os.environ["AWS_REGION"] = args["AWS_REGION"]
os.environ["TLC_MONTHS"] = args["TLC_MONTHS"]
os.environ["PSEUDO_SALT"] = args["PSEUDO_SALT"]

import ingest  # noqa: E402  (uploadé à plat par Terraform)

ingest.main(ingest.get_months())
