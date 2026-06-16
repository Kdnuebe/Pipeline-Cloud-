# Valeurs utiles affichées après `terraform apply` (à noter pour la démo/le rapport).
output "data_lake_bucket" {
  description = "Nom du bucket S3 (data lake + code + résultats Athena)."
  value       = aws_s3_bucket.lake.id
}

output "api_url" {
  description = "URL publique de l'API REST gold (tester /health, /zones/top, /docs via openapi)."
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "state_machine_arn" {
  description = "ARN de la pipeline Step Functions (à déclencher pour lancer un run)."
  value       = aws_sfn_state_machine.pipeline.arn
}

output "athena_database" {
  description = "Base de données Glue/Athena contenant les tables silver/gold."
  value       = aws_glue_catalog_database.db.name
}

output "sns_topic_arn" {
  description = "Topic SNS des alertes (penser à confirmer l'abonnement email)."
  value       = aws_sns_topic.alerts.arn
}

output "cloudwatch_dashboard" {
  description = "Nom du tableau de bord CloudWatch d'observabilité."
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}
