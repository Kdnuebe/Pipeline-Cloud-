# =============================================================================
# LAMBDA — API REST gold (handler boto3, zéro dépendance externe -> zip léger).
# =============================================================================
data "archive_file" "api" {
  type        = "zip"
  source_file = "${path.module}/../api/lambda_handler.py"
  output_path = "${path.module}/build/api_lambda.zip"
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.project_prefix}-api"
  role             = aws_iam_role.lambda.arn
  handler          = "lambda_handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.api.output_path
  source_code_hash = data.archive_file.api.output_base64sha256
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      ATHENA_DB        = aws_glue_catalog_database.db.name
      ATHENA_OUTPUT    = local.athena_output
      DATA_LAKE_BUCKET = aws_s3_bucket.lake.id
      # NB : AWS_REGION est fournie automatiquement par le runtime Lambda (variable réservée).
    }
  }
}
