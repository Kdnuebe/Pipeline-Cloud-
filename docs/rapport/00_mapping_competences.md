# 0 bis. Validation des compétences — Blocs 2 & 3

Ce tableau relie chaque compétence des blocs à un élément **concret et démontrable** du projet
(à montrer en soutenance). Niveau : 🟢 fort · 🟡 partiel.

## Bloc 3 — Stockage & traitement de données sur le cloud  *(cœur du projet)*

| Compétence | Comment c'est validé | Preuve | Niveau |
|---|---|---|---|
| Mettre en œuvre des solutions de **stockage cloud** (types de stockage & archivage) | S3 + format **Parquet** compressé ; **cycle de vie** Standard → IA (30 j) → **Glacier** (90 j) | `cloud_simple/s3_lifecycle.json`, [04_formats_stockage.md] | 🟢 |
| Concevoir/développer des **pipelines cloud** (charger, transformer, mettre à disposition) | Chargement S3 (bronze) → **Athena** transforme (silver/gold) → mise à dispo via **API + dashboard** | `cloud_simple/athena/`, `api/`, `dashboard/` | 🟢 |
| Mettre en place une **politique de sécurité** (chiffrement, IAM, RGPD, conformité) | **Chiffrement S3** (SSE) ; **IAM** moindre privilège ; **pseudonymisation** + **k-anonymat** ; registre de traitement | [08_rgpd.md], guide Partie 6 | 🟢 |
| **Optimiser** stockage/traitement (indicateurs de perf, disponibilité, coûts) | **FinOps** chiffré ; indicateur Athena « **Data scanned** » ; partitionnement & Parquet ; lifecycle | [07_finops.md], `finops/cost_calculator.py` | 🟢 |

## Bloc 2 — Concevoir, développer & déployer une solution de traitement de données massives

| Compétence | Comment c'est validé | Preuve | Niveau |
|---|---|---|---|
| **Architecture distribuée** pour traiter des données massives | **Athena** = moteur SQL **distribué, serverless** (Presto) sur **S3** (stockage distribué) ; ~3 M lignes/mois | [03_architecture.md] | 🟢 |
| Transformer des données de **sources variées**, analytique **à l'échelle**, données **multidimensionnelles** | **3 sources** jointes (taxi + zones + météo) ; datamarts **multidimensionnels** (zone × heure × jour) | `transformations/sql/`, [09_interpretations_metier.md] | 🟢 |
| **Optimiser la performance** des pipelines (intégration & mise en scène) | Partitionnement `year/month`, Parquet (pruning Athena), échantillonnage ML, filtres qualité en amont | [04_formats_stockage.md], [07_finops.md] | 🟢 |
| **Automatiser** création/tests/intégration/déploiement (**conteneurisation & ordonnancement**) | **AWS Step Functions** orchestre les transformations (retry + alerte) ; orchestrateur local `run_local_pipeline.py` ; **tests qualité auto** ; **Dockerfile** ; **CI GitHub Actions** ; planification (cron/Task Scheduler) | `cloud_simple/stepfunctions/`, `run_local_pipeline.py`, `Dockerfile`, `.github/workflows/ci.yml` | 🟢 |
| Implémenter un système distribué de **streaming** (temps quasi réel) | **Non couvert** par ce projet (traitement **batch**). À traiter via un autre projet du cursus (Big Data Frameworks / streaming). Extension possible : ingestion micro-batch (Kinesis). | — | ⬜ |

> **Honnêteté en soutenance** : le seul point non couvert est le **streaming temps réel** (notre
> pipeline est en *batch*). C'est normal : le diaporama du diplôme montre que le Bloc 2 est validé par
> **plusieurs projets** ; celui-ci en couvre 4 compétences sur 5. Pouvoir dire clairement ce qui est
> couvert **et ce qui ne l'est pas** est apprécié par un jury.

## Phrase de synthèse (à dire au jury)
> « Ce projet implémente une plateforme de données complète sur le cloud AWS : stockage S3 optimisé,
> traitement SQL distribué avec Athena, sécurité et conformité RGPD, analyse de coûts FinOps, et un
> modèle de machine learning intégré. Il valide l'intégralité du Bloc 3 et l'essentiel du Bloc 2, à
> l'exception du streaming temps réel, couvert par ailleurs. »
