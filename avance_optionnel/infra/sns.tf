# =============================================================================
# SNS — Canal d'alerting (email). L'abonnement doit être CONFIRMÉ via le lien reçu.
# =============================================================================
resource "aws_sns_topic" "alerts" {
  name = "${var.project_prefix}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
