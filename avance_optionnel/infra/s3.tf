# =============================================================================
# S3 — Data lake unique (couches bronze/silver/gold + code + sql + résultats Athena)
# Un seul bucket pour simplifier (et réduire les coûts). Chiffré, privé.
# =============================================================================
resource "aws_s3_bucket" "lake" {
  bucket        = local.bucket_name
  force_destroy = true # permet `terraform destroy` même si le bucket contient des objets
}

# Chiffrement au repos (RGPD : SSE-S3 activé dès l'ingestion)
resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

# Aucun accès public (RGPD : bronze jamais exposé)
resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Politique de cycle de vie (FinOps + rétention RGPD)
resource "aws_s3_bucket_lifecycle_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    id     = "bronze-archive"
    status = "Enabled"
    filter { prefix = "bronze/" }
    transition {
      days          = 30
      storage_class = "STANDARD_IA" # bronze rarement relu après 30j -> moins cher
    }
  }
  rule {
    id     = "athena-results-cleanup"
    status = "Enabled"
    filter { prefix = "athena-results/" }
    expiration { days = 7 } # les résultats de requêtes sont jetables
  }
}

# -----------------------------------------------------------------------------
# Upload du CODE réutilisé par les jobs Glue (--extra-py-files) et des SQL.
# etag = md5 -> Terraform ré-uploade automatiquement si le fichier change.
# -----------------------------------------------------------------------------
locals {
  code_files = {
    "code/pipeline_common.py" = "${path.module}/../pipeline_common.py"
    "code/ingest.py"          = "${path.module}/../data_ingestion/ingest.py"
    "code/checks.py"          = "${path.module}/../quality/checks.py"
    "code/train_score.py"     = "${path.module}/../ml/train_score.py"
    "code/glue_ingest.py"     = "${path.module}/../cloud/glue/glue_ingest.py"
    "code/glue_transform.py"  = "${path.module}/../cloud/glue/glue_transform.py"
    "code/glue_quality.py"    = "${path.module}/../cloud/glue/glue_quality.py"
    "code/glue_ml.py"         = "${path.module}/../cloud/glue/glue_ml.py"
    "sql/silver_trips.sql"               = "${path.module}/../transformations/sql/silver_trips.sql"
    "sql/gold_demand_by_zone_hour.sql"   = "${path.module}/../transformations/sql/gold_demand_by_zone_hour.sql"
    "sql/gold_tips_analysis.sql"         = "${path.module}/../transformations/sql/gold_tips_analysis.sql"
  }
}

resource "aws_s3_object" "artifacts" {
  for_each = local.code_files
  bucket   = aws_s3_bucket.lake.id
  key      = each.key
  source   = each.value
  etag     = filemd5(each.value)
}
