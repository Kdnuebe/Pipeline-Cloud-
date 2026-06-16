"""
DAG Airflow (OPTIONNEL) — miroir local de la pipeline, pour visualiser le graphe
de dépendances et démontrer retry / scheduling / alerte d'échec.

NB : l'orchestrateur NOTÉ du projet est AWS Step Functions (cloud). Ce DAG sert
surtout à produire une belle capture "graph view" et à montrer la même logique
d'orchestration en local. Le chemin local le plus simple reste run_local_pipeline.py.

Le projet est monté dans le conteneur sous /opt/project (voir local/docker-compose.yml).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/project"
ENV = "cd " + PROJECT + " && DATA_ROOT=" + PROJECT + "/data "

default_args = {
    "owner": "data-eng",
    "retries": 2,                       # retry automatique en cas d'échec transitoire
    "retry_delay": timedelta(seconds=30),
}

with DAG(
    dag_id="nyc_taxi_medallion",
    description="Bronze -> Silver/Gold -> Qualité -> ML",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",                  # scheduling
    catchup=False,
    default_args=default_args,
    tags=["medallion", "nyc-taxi"],
) as dag:

    bronze = BashOperator(
        task_id="bronze_ingest",
        bash_command=ENV + "python data_ingestion/ingest.py",
    )
    silver_gold = BashOperator(
        task_id="silver_gold_transform",
        bash_command=ENV + "python transformations/run_local.py",
    )
    quality = BashOperator(
        task_id="quality_checks",
        bash_command=ENV + "python quality/checks.py",
    )
    ml = BashOperator(
        task_id="ml_train_score",
        bash_command=ENV + "python ml/train_score.py",
    )

    # Dépendances : chaque étape attend la précédente
    bronze >> silver_gold >> quality >> ml
