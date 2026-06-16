# =============================================================================
# IAM — Rôles à moindre privilège pour Glue, Step Functions et Lambda.
# =============================================================================
locals {
  bucket_arn = aws_s3_bucket.lake.arn
}

# --- Politique S3 commune (lecture/écriture sur NOTRE bucket uniquement) ------
data "aws_iam_policy_document" "s3_access" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${local.bucket_arn}/*"]
  }
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [local.bucket_arn]
  }
}

# --- Politique Athena + Glue Data Catalog ------------------------------------
data "aws_iam_policy_document" "athena_glue" {
  statement {
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution",
      "athena:GetQueryResults", "athena:StopQueryExecution", "athena:GetWorkGroup"
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "glue:GetDatabase", "glue:GetDatabases", "glue:CreateDatabase",
      "glue:GetTable", "glue:GetTables", "glue:CreateTable", "glue:UpdateTable",
      "glue:DeleteTable", "glue:GetPartition", "glue:GetPartitions",
      "glue:BatchCreatePartition", "glue:CreatePartition"
    ]
    resources = ["*"]
  }
}

# ----------------------------- Rôle GLUE -------------------------------------
data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "${var.project_prefix}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

resource "aws_iam_role_policy_attachment" "glue_managed" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3" {
  name   = "s3-access"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_role_policy" "glue_athena" {
  name   = "athena-glue"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.athena_glue.json
}

resource "aws_iam_role_policy" "glue_cloudwatch" {
  name = "cloudwatch-metrics"
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["cloudwatch:PutMetricData"], Resource = "*" }]
  })
}

# ----------------------- Rôle STEP FUNCTIONS ---------------------------------
data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${var.project_prefix}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

resource "aws_iam_role_policy" "sfn_policy" {
  name = "sfn-permissions"
  role = aws_iam_role.sfn.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["glue:StartCrawler", "glue:GetCrawler",
          "glue:StartJobRun", "glue:GetJobRun", "glue:BatchStopJobRun"]
        Resource = "*"
      },
      { Effect = "Allow", Action = ["sns:Publish"], Resource = aws_sns_topic.alerts.arn }
    ]
  })
}

# ----------------------------- Rôle LAMBDA -----------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3" {
  name   = "s3-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_role_policy" "lambda_athena" {
  name   = "athena-glue"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.athena_glue.json
}
