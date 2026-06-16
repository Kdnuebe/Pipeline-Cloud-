# =============================================================================
# GLUE — Catalogue de données, crawler (bronze) et 4 jobs Python Shell.
# =============================================================================
resource "aws_glue_catalog_database" "db" {
  name = replace("${var.project_prefix}_db", "-", "_")
}

# Crawler : catalogue les données bronze (préfixe "bronze_" -> bronze_trips, ...)
resource "aws_glue_crawler" "bronze" {
  name          = "${var.project_prefix}-bronze-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.db.name
  table_prefix  = "bronze_"

  s3_target {
    path = "s3://${aws_s3_bucket.lake.id}/bronze/"
  }

  # Le crawler accepte les schémas qui évoluent d'un mois à l'autre
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
}

locals {
  glue_common_args = {
    "--DATA_LAKE_BUCKET" = aws_s3_bucket.lake.id
    "--AWS_REGION"       = var.aws_region
    "--TempDir"          = "s3://${aws_s3_bucket.lake.id}/glue-tmp/"
    "--job-language"     = "python"
  }
  athena_db = aws_glue_catalog_database.db.name
}

# --- Job 1 : INGESTION (bronze) ---------------------------------------------
resource "aws_glue_job" "ingest" {
  name         = "${var.project_prefix}-ingest"
  role_arn     = aws_iam_role.glue.arn
  max_capacity = 1.0
  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_bucket.lake.id}/code/glue_ingest.py"
  }
  default_arguments = merge(local.glue_common_args, {
    "--extra-py-files"            = "s3://${aws_s3_bucket.lake.id}/code/pipeline_common.py,s3://${aws_s3_bucket.lake.id}/code/ingest.py"
    "--additional-python-modules" = "pyarrow,requests,python-dotenv"
    "--TLC_MONTHS"                = var.tlc_months
    "--PSEUDO_SALT"               = var.pseudo_salt
  })
  depends_on = [aws_s3_object.artifacts]
}

# --- Job 2 : TRANSFORM (silver + gold via Athena) ---------------------------
resource "aws_glue_job" "transform" {
  name         = "${var.project_prefix}-transform"
  role_arn     = aws_iam_role.glue.arn
  max_capacity = 1.0
  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_bucket.lake.id}/code/glue_transform.py"
  }
  default_arguments = merge(local.glue_common_args, {
    "--ARTIFACTS_BUCKET" = aws_s3_bucket.lake.id
    "--ATHENA_DB"        = local.athena_db
    "--ATHENA_OUTPUT"    = local.athena_output
  })
  depends_on = [aws_s3_object.artifacts]
}

# --- Job 3 : QUALITÉ ---------------------------------------------------------
resource "aws_glue_job" "quality" {
  name         = "${var.project_prefix}-quality"
  role_arn     = aws_iam_role.glue.arn
  max_capacity = 1.0
  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_bucket.lake.id}/code/glue_quality.py"
  }
  default_arguments = merge(local.glue_common_args, {
    "--extra-py-files"            = "s3://${aws_s3_bucket.lake.id}/code/pipeline_common.py,s3://${aws_s3_bucket.lake.id}/code/checks.py"
    "--additional-python-modules" = "pyarrow"
  })
  depends_on = [aws_s3_object.artifacts]
}

# --- Job 4 : ML (bonus) ------------------------------------------------------
resource "aws_glue_job" "ml" {
  name         = "${var.project_prefix}-ml"
  role_arn     = aws_iam_role.glue.arn
  max_capacity = 1.0
  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_bucket.lake.id}/code/glue_ml.py"
  }
  default_arguments = merge(local.glue_common_args, {
    "--extra-py-files"            = "s3://${aws_s3_bucket.lake.id}/code/pipeline_common.py,s3://${aws_s3_bucket.lake.id}/code/train_score.py"
    "--additional-python-modules" = "pyarrow,scikit-learn"
    "--ML_SAMPLE_ROWS"            = var.ml_sample_rows
    "--ATHENA_DB"                 = local.athena_db
    "--ATHENA_OUTPUT"             = local.athena_output
  })
  depends_on = [aws_s3_object.artifacts]
}
