# 5. Orchestration & automatisation

Le projet utilise **deux niveaux d'orchestration complémentaires**, des plus simple au plus « cloud » :

## A. Orchestrateur local — `run_local_pipeline.py` (développement & secours)
Un script Python qui enchaîne les étapes, **que l'on comprend ligne par ligne** :

```
Bronze (ingestion) → Silver/Gold (SQL) → Qualité (tests) → ML
```

| Exigence (PDF) | Mise en œuvre |
|---|---|
| **Dépendances** | Enchaînement séquentiel (chaque étape attend la précédente) |
| **Retry** | 2 nouvelles tentatives par étape (délai 8 s) avant abandon |
| **Alertes d'échec** | Alerte console + **email SNS** si `ALERT_SNS_TOPIC_ARN` configuré |
| **Scheduling** | Planificateur Windows / **cron** (commande en tête du script) |
| **Monitoring** | Rapport de run (`data/pipeline_run_report.json`) : durée, lignes, taux d'erreur |
| **Tests intégrés** | L'étape « Qualité » bloque la suite si un test critique échoue |

## B. Orchestrateur cloud — AWS Step Functions (transformations Athena)
Pour l'**orchestration dans le cloud** (l'outil cité en premier par le PDF), une **state machine
Step Functions** enchaîne les transformations **Athena** : `BuildSilver → BuildGoldDemand →
BuildGoldTips → Success`, avec **retry** (sur erreurs Athena) et **alerte d'échec → SNS (email)**.

- Définition : `cloud_simple/stepfunctions/state_machine.asl.json`
- Créée **à la console** (ou en 4 commandes CLI) — **sans Terraform, sans Glue, sans Lambda**.
- Avantage soutenance : un **graphe d'exécution visuel** qui passe au vert.
- Mise en place : `cloud_simple/stepfunctions/README.md`.

> Partage des rôles : **ingestion + ML** restent en local (calcul Python) ; **Step Functions** orchestre
> uniquement les **transformations SQL Athena**, qui ne demandent aucun serveur.

## Comparatif des orchestrateurs

| Critère | Script Python | **Step Functions** (retenu cloud) | Airflow / MWAA |
|---|---|---|---|
| Coût | ✅ 0 | ✅ ~0 (free tier 4000 transitions/mois) | ❌ MWAA ~350 €/mois |
| Mise en place | ✅ immédiate | ✅ console (pas de Terraform) | ❌ Docker/serveur |
| Natif AWS / visuel | ⚠️ texte | ✅ **graphe visuel, intégration Athena native** | ⚠️ |
| Maîtrise / explicabilité | ✅ on lit le code | ✅ JSON ASL lisible | ⚠️ |
| **Décision** | Gardé en **local** (dev + secours). | **Retenu pour le cloud** : natif, visuel, gratuit. | Écarté (coût/complexité). |

> **Pour aller plus loin** : la version `avance_optionnel/` pousse l'industrialisation complète
> (Step Functions + **Glue** + **Lambda** + **Terraform** : tout tourne dans le cloud, planifié,
> sans PC). À citer en soutenance comme évolution possible.
