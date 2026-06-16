# 🚕 Pipeline Data Médaillon — NYC Yellow Taxi (AWS, version simple)

Pipeline de données **Bronze → Silver → Gold** : du fichier brut jusqu'aux tableaux de bord, avec
qualité, ML, sécurité/RGPD et analyse des coûts. Conçu pour être **simple, maîtrisable et présentable**
(soutenance de mémoire), et pour valider les **Blocs 2 & 3**.

> 👉 **Commence ici : [docs/00_GUIDE_PAS_A_PAS.md](docs/00_GUIDE_PAS_A_PAS.md)**
> 👉 **Pour le jury : [docs/rapport/00_resume_executif.md](docs/rapport/00_resume_executif.md)** (vulgarisé)
> 👉 **Validation des blocs : [docs/rapport/00_mapping_competences.md](docs/rapport/00_mapping_competences.md)**

## Le cloud en services simples
| Service AWS | Rôle (1 phrase) |
|---|---|
| **Amazon S3** | le « disque dur du cloud » : stocke bronze/silver/gold |
| **Amazon Athena** | exécute du **SQL** sur les fichiers S3, sans serveur (le traitement cloud) |
| **AWS Step Functions** | **orchestre** les transformations Athena (graphe visuel + alerte) — créé à la console |

*(Pas de Terraform, pas de Glue, pas de Lambda. La version pleinement « industrialisée » est rangée
dans `avance_optionnel/` — à mentionner en soutenance, pas à déployer.)*

## Ce qui marche déjà (validé en local sur données réelles)
- **2 964 624** courses ingérées (2024-01) + zones + météo
- Nettoyage/jointures/RGPD → **2 717 423** lignes silver · datamarts gold
- **ML : MAE 3,09 $ vs 13,96 $ baseline (−77,8 %), R² 0,92**
- Qualité **9/9 tests** · API (FastAPI) + Dashboard (Streamlit)

## Démarrage rapide (local, gratuit)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run_local_pipeline.py 2024-01     # toute la pipeline (~2 min)
streamlit run dashboard/app.py           # dashboard
uvicorn api.app:app --reload             # API + Swagger (/docs)
```

## Cloud (S3 + Athena + Step Functions) — résumé
1. `aws s3 cp data/bronze s3://VOTRE-BUCKET/bronze --recursive`
2. Dans Athena, exécuter `cloud_simple/athena/01` (tables bronze), puis `04` (exploration).
3. Orchestrer `silver → gold` avec **Step Functions** (`cloud_simple/stepfunctions/README.md`) —
   ou lancer `02`/`03` à la main dans Athena.
→ détails dans le guide.

## Structure
```
data_ingestion/   Bronze (ingest.py)
transformations/  SQL portable (DuckDB local) + run_local.py
quality/          Tests de qualité (checks.py)
ml/               Bonus ML (train_score.py)
api/              API REST (FastAPI) + openapi.yaml
dashboard/        Dashboard Streamlit
cloud_simple/     ☁️ Scripts Athena + lifecycle (la version simple à présenter)
finops/           Calculateur de coûts
docs/             Guide + rapport (résumé exécutif, mapping blocs, 9 sections) + diagramme + script vidéo
avance_optionnel/ Version industrialisée (Terraform/Glue/Step Functions) — NON requise
```

## Coût
Local : **0 €**. Cloud (S3 + Athena, démo) : **quelques centimes** (voir [docs/rapport/07_finops.md](docs/rapport/07_finops.md)).
```
