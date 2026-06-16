# =============================================================================
# EVENTBRIDGE — Scheduling (déclenchement quotidien automatique de la pipeline).
# Désactivé par défaut (var.enable_schedule=false) pour éviter tout coût subi :
# en démo on déclenche manuellement. Mettre à true pour un run quotidien réel.
# =============================================================================
resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.project_prefix}-daily"
  description         = "Déclenche la pipeline une fois par jour."
  schedule_expression = "rate(1 day)"
  state               = var.enable_schedule ? "ENABLED" : "DISABLED"
}

# Rôle permettant à EventBridge de démarrer la state machine.
data "aws_iam_policy_document" "events_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "events" {
  name               = "${var.project_prefix}-events-role"
  assume_role_policy = data.aws_iam_policy_document.events_assume.json
}

resource "aws_iam_role_policy" "events" {
  name = "start-execution"
  role = aws_iam_role.events.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["states:StartExecution"], Resource = aws_sfn_state_machine.pipeline.arn }]
  })
}

resource "aws_cloudwatch_event_target" "daily" {
  rule     = aws_cloudwatch_event_rule.daily.name
  arn      = aws_sfn_state_machine.pipeline.arn
  role_arn = aws_iam_role.events.arn
}
