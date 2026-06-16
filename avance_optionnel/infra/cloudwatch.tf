# =============================================================================
# CLOUDWATCH — Monitoring (dashboard) + Alerting (alarme -> SNS).
# =============================================================================

# Alarme : déclenche une alerte si une exécution de la pipeline ÉCHOUE.
resource "aws_cloudwatch_metric_alarm" "pipeline_failed" {
  alarm_name          = "${var.project_prefix}-pipeline-failed"
  alarm_description   = "Au moins une exécution de la pipeline a échoué."
  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  dimensions          = { StateMachineArn = aws_sfn_state_machine.pipeline.arn }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# Alarme métier : trop de tests qualité en échec (métrique custom TaxiPipeline).
resource "aws_cloudwatch_metric_alarm" "quality_failed" {
  alarm_name          = "${var.project_prefix}-quality-failed"
  alarm_description   = "Des tests de qualité de données ont échoué."
  namespace           = "TaxiPipeline"
  metric_name         = "QualityFailedChecks"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# Tableau de bord d'observabilité (lignes traitées, MAE du modèle, échecs qualité).
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_prefix}-observabilite"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6,
        properties = {
          title  = "Lignes traitées par couche",
          region = var.aws_region,
          metrics = [
            ["TaxiPipeline", "RowsProcessed", "layer", "silver"],
            ["TaxiPipeline", "RowsProcessed", "layer", "gold", "table", "demand_by_zone_hour"]
          ],
          view = "timeSeries", stat = "Maximum"
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6,
        properties = {
          title   = "Qualité & ML",
          region  = var.aws_region,
          metrics = [["TaxiPipeline", "QualityFailedChecks"], ["TaxiPipeline", "MLModelMAE"]],
          view    = "timeSeries", stat = "Maximum"
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6,
        properties = {
          title  = "Exécutions de la pipeline (Step Functions)",
          region = var.aws_region,
          metrics = [
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.pipeline.arn],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.pipeline.arn]
          ],
          view = "timeSeries", stat = "Sum"
        }
      }
    ]
  })
}
