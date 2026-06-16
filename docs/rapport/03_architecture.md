# 3. Architecture

## Vue d'ensemble
Architecture **médaillon Bronze → Silver → Gold**, volontairement **simple et serverless**. Côté
données, le cloud se limite à **deux services faciles** (S3 + Athena) ; l'orchestration des
transformations est confiée à **Step Functions**. Voir le diagramme `docs/architecture.mmd`.

```
Sources (TLC, zones, météo)
      │  Python (run_local_pipeline.py) : ingestion + ML
      ▼
   S3 bronze/  (Parquet, chiffré)                         ← stockage cloud
      │  Amazon Athena : SQL CTAS (nettoyage, jointures, RGPD)  ← traitement cloud
      ▼                         (orchestré par AWS Step Functions : retry + alerte)
   S3 silver/trips  →  tests qualité (checks.py)
      │  Athena : SQL CTAS (agrégats)
      ▼
   S3 gold/ demand_by_zone_hour · tips_analysis · ml_predictions
      │
      ├─ API REST (FastAPI, exécutée en local) + Swagger
      └─ Dashboard (Streamlit)
```

## Les services cloud (et pourquoi)

| Service | Rôle | Pourquoi ce choix |
|---|---|---|
| **Amazon S3** | Stockage des fichiers (bronze/silver/gold) en Parquet | Stockage objet **durable, peu cher, chiffré**, standard du data lake |
| **Amazon Athena** | Exécute du **SQL** directement sur S3, sans serveur | **Distribué, serverless, payé à l'usage** ; on écrit du SQL qu'on comprend |
| **AWS Step Functions** | **Orchestre** les transformations Athena (silver → gold) | Natif AWS, **graphe visuel**, retry + alerte intégrés, gratuit (free tier) |

> **Choix assumé de simplicité** : on n'utilise volontairement **ni Glue, ni Lambda, ni Terraform**.
> Ces outils « industrialisent » la pipeline mais ajoutent de la complexité invisible. **S3 + Athena +
> Step Functions** (tous créés à la console) suffisent à démontrer toutes les compétences
> (cf. `00_mapping_competences.md`). La version pleinement industrialisée (avec Glue, Lambda et
> Terraform) est fournie en annexe (`avance_optionnel/`) et citée comme évolution possible.

## Pourquoi Athena = « architecture distribuée » (Bloc 2)
Athena s'appuie sur **Presto/Trino**, un moteur de requêtes **distribué** : la requête est découpée
et exécutée en parallèle sur de nombreux nœuds gérés par AWS, directement sur les fichiers S3. On
bénéficie donc d'un traitement distribué de données massives **sans gérer le moindre serveur ni
cluster** — l'essence du serverless.

## Le SQL : un seul code, deux moteurs
Les transformations sont écrites en **SQL** (dossier `transformations/sql/` pour le local,
`cloud_simple/athena/` pour le cloud). En local on les exécute avec **DuckDB** (gratuit, instantané) ;
sur AWS, le **même SQL** tourne dans **Athena**. Cela permet de tout tester gratuitement avant de
toucher au cloud.

## Environnement de développement (coût 0 €)
`run_local_pipeline.py` + DuckDB reproduisent toute la chaîne en local : on développe et on valide
sans dépenser, puis on rejoue sur AWS pour la démonstration.
