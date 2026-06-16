variable "aws_region" {
  description = "Région AWS (eu-west-3 = Paris)."
  type        = string
  default     = "eu-west-3"
}

variable "project_prefix" {
  description = "Préfixe des ressources (le bucket devient <prefix>-<suffixe aléatoire>)."
  type        = string
  default     = "nyc-taxi-pipeline"
}

variable "alert_email" {
  description = "Email qui recevra les alertes SNS (à confirmer via le lien reçu)."
  type        = string
}

variable "tlc_months" {
  description = "Mois TLC à ingérer (démo rapide : 1 mois)."
  type        = string
  default     = "2024-01"
}

variable "pseudo_salt" {
  description = "Sel de pseudonymisation RGPD."
  type        = string
  default     = "change-me-in-prod"
  sensitive   = true
}

variable "ml_sample_rows" {
  description = "Nombre de lignes pour l'échantillon d'entraînement ML."
  type        = string
  default     = "200000"
}

variable "enable_schedule" {
  description = "Active le déclenchement quotidien automatique (false = manuel, évite les coûts)."
  type        = bool
  default     = false
}
