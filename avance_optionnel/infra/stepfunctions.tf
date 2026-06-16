# =============================================================================
# STEP FUNCTIONS — Orchestrateur de la pipeline (DAG cloud).
# La définition vient de cloud/stepfunctions/state_machine.asl.json (placeholders
# remplacés par templatefile).
# =============================================================================
resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project_prefix}-pipeline"
  role_arn = aws_iam_role.sfn.arn

  definition = templatefile("${path.module}/../cloud/stepfunctions/state_machine.asl.json", {
    crawler_name   = aws_glue_crawler.bronze.name
    transform_job  = aws_glue_job.transform.name
    quality_job    = aws_glue_job.quality.name
    ml_job         = aws_glue_job.ml.name
    sns_topic_arn  = aws_sns_topic.alerts.arn
  })
}
