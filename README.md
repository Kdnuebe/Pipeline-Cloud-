# Pipeline Data Médaillon — NYC Yellow Taxi (AWS)

Pipeline de données **Bronze → Silver → Gold** : du fichier brut jusqu'aux datamarts, à une API REST,
un dashboard et un modèle de Machine Learning. Conçue pour être **simple, gratuite à développer, et
déployable sur AWS** (S3 + Athena + Step Functions), sans Terraform.

> 📖 **Guide pas-à-pas complet → [docs/00_GUIDE_PAS_A_PAS.md](docs/00_GUIDE_PAS_A_PAS.md)**

## Le cloud en 3 services simples
| Service AWS | Rôle |
|---|---|
| **Amazon S3** | stocke les fichiers (bronze/silver/gold), chiffrés |
| **Amazon Athena** | exécute du **SQL** sur S3, sans serveur (le traitement) |
| **AWS Step Functions** | **orchestre** les transformations (graphe visuel + alerte email) |

## Démarrage rapide — en local (gratuit, ~2 min)
```bash
python -m venv .venv
# Windows :  .\.venv\Scripts\activate   |  macOS/Linux :  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # Windows : copy .env.example .env

python run_local_pipeline.py 2024-01      # toute la pipeline : bronze → silver → gold → qualité → ML
streamlit run dashboard/app.py            # dashboard      → http://localhost:8501
uvicorn api.app:app --reload              # API + Swagger  → http://localhost:8000/docs
```

## Déploiement sur AWS
Après `aws configure`, **tout se déploie en une commande** :
```bash
python cloud_simple/deploy.py --email votre@email.com
```
Cela crée le bucket S3, charge les données, construit silver/gold via **Athena**, orchestré par
**Step Functions**, et met en place les alertes. Détails (et version manuelle à la console) dans le
[guide](docs/00_GUIDE_PAS_A_PAS.md). Pour tout supprimer : `python cloud_simple/teardown.py`.

## Ce que fait la pipeline
- **~3 M lignes/mois** ingérées (taxi + zones + météo), nettoyées et enrichies
- **Datamarts** : demande par zone/heure, analyse des pourboires, prédictions ML
- **ML** : estimation du prix d'une course (erreur ~4× plus faible qu'une baseline) + détection d'anomalies
- **Qualité** : 9 tests automatisés · **RGPD** : pseudonymisation + k-anonymat · **FinOps** : ~0 €

## Structure
```
data_ingestion/      Bronze : ingestion des données brutes
transformations/     Silver & Gold : SQL (DuckDB en local, Athena dans le cloud)
quality/             Tests de qualité des données
ml/                  Modèle de Machine Learning
api/                 API REST (FastAPI) + spec OpenAPI
dashboard/           Tableau de bord (Streamlit)
cloud_simple/        Déploiement AWS : scripts Athena, Step Functions, deploy.py / teardown.py
finops/              Estimation des coûts
tests/               Tests automatisés (lancés par la CI)
run_local_pipeline.py  Orchestrateur local (enchaîne toutes les étapes)
docs/                Guide pas-à-pas + diagramme d'architecture
```

## Stack technique
Python · Amazon S3 · Amazon Athena · AWS Step Functions · Amazon SNS · AWS IAM · DuckDB · Parquet ·
pandas · scikit-learn · FastAPI · Streamlit · Docker · GitHub Actions.

## Licence / contexte
Projet pédagogique (Master 2 Data Engineering). Données : NYC TLC (open data) + Open-Meteo.
