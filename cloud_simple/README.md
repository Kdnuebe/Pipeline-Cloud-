# ☁️ Version cloud SIMPLE (S3 + Athena, sans Terraform)

Cette version est celle que **tu présentes et maîtrises**. Le cloud se résume à **2 services
faciles à comprendre** :

| Service AWS | Rôle (en une phrase) | Ce que tu fais |
|---|---|---|
| **Amazon S3** | Le « disque dur du cloud » : stocke les fichiers (bronze/silver/gold) | Créer un bucket, uploader, régler l'archivage |
| **Amazon Athena** | Un moteur qui exécute du **SQL** directement sur les fichiers S3, sans serveur | Coller et exécuter les scripts SQL |

> Pas de Terraform, pas de Glue, pas de Lambda. Tout se fait dans la **console AWS** (visuel, parfait
> pour les captures) + quelques commandes simples. En option, **AWS Step Functions** (créé aussi à la
> console) orchestre les transformations Athena — voir `stepfunctions/`.

## Le principe en 1 image
```
PC (local, gratuit)                         AWS (cloud)
─────────────────────                       ─────────────────────────────
run_local_pipeline.py  ──upload S3──►  S3 bronze/  ──Athena SQL──►  S3 silver/ + gold/
(produit data/bronze)                       (le CLOUD transforme via SQL)         │
                                                                                  ▼
                                                                    Dashboard / API (lus en local)
```

## Étapes (détaillées dans `docs/00_GUIDE_PAS_A_PAS.md`)
1. **Local** : `python run_local_pipeline.py 2024-01` → crée `data/bronze`, `data/silver`, `data/gold`.
2. **S3** : créer un bucket, uploader `data/bronze` (et `data/gold/ml_predictions`).
3. **Athena** : exécuter dans l'ordre les scripts de `athena/` :
   - `01_create_bronze_tables.sql` — déclare les tables sur les fichiers S3
   - `02_build_silver.sql` — le cloud nettoie/joint/anonymise (CTAS)
   - `03_build_gold.sql` — le cloud agrège (datamarts) + table ML
   - `04_explore.sql` — requêtes métier (captures + réponses aux problématiques)
4. **Orchestration (recommandé)** : au lieu de lancer `02`/`03` à la main, **AWS Step Functions**
   enchaîne les transformations Athena automatiquement (graphe visuel + alerte email). Voir
   `stepfunctions/README.md`.
5. **Sécurité / archivage** : chiffrement S3, lifecycle (`s3_lifecycle.json`), IAM (voir guide).

## Pourquoi c'est suffisant pour valider les blocs
- **Bloc 3** (stockage cloud, traitement cloud, sécurité, optimisation) : S3 + Athena + IAM +
  chiffrement + lifecycle + indicateurs de coût/perf. ✅
- **Bloc 2** (architecture distribuée, transformation multi-sources, optimisation) : Athena = moteur
  SQL **distribué serverless** ; 3 sources jointes ; partitionnement/Parquet pour la perf. ✅

Voir `docs/rapport/00_mapping_competences.md` pour le détail compétence par compétence.
