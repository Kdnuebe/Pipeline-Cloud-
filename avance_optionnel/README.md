# 📦 Version avancée (OPTIONNELLE — tu n'as PAS besoin d'y toucher)

Ce dossier contient une version **industrialisée** de la pipeline, conservée à part pour ne pas
alourdir le projet. **Le projet que tu présentes utilise la version SIMPLE** (S3 + Athena via la
console), décrite dans `docs/00_GUIDE_PAS_A_PAS.md` et `cloud_simple/`.

Garde ce dossier uniquement pour **en parler en soutenance** comme « industrialisation possible »
(ça montre ta culture technique), sans avoir à le déployer.

## Contenu
- `infra/` — **Terraform** (infrastructure-as-code) : déploierait automatiquement toute l'infra.
- `cloud/glue/` — jobs **AWS Glue** (exécuteraient la pipeline sans PC).
- `cloud/stepfunctions/` — **Step Functions** (orchestration automatique dans le cloud).
- `lambda_handler.py` — l'API en version **AWS Lambda** (serverless).
- `orchestration/airflow/` + `local/` — **Airflow** (orchestrateur visuel) via Docker.

## Phrase à dire en soutenance (si on te pose la question « comment industrialiser ? »)
> « La version de démonstration est pilotée manuellement pour la maîtriser de bout en bout. Pour
> industrialiser, j'ai préparé une version Infrastructure-as-Code (Terraform) qui déploie
> automatiquement le stockage, l'orchestration (Step Functions), les traitements (Glue) et l'API
> (Lambda) — la pipeline tournerait alors toute seule, planifiée et sans intervention. »

> ⚠️ Les chemins relatifs dans `infra/` (Terraform) supposent l'ancienne arborescence : à ajuster
> si un jour tu veux réellement la déployer. Non nécessaire pour le rendu.
