# 1. Thématique & données

## Thématique
Analyse de la **mobilité urbaine via les taxis jaunes de New York (NYC Yellow Taxi)**,
enrichie par la **météo** et le **référentiel géographique des zones**. Cas d'usage typique
d'une plateforme data : volumétrie massive, données temporelles, enjeux métier clairs
(demande, revenus, qualité de service) et possibilité de prédiction.

## Jeux de données (3 entités joinables)

| Source | Contenu | Volume | Fraîcheur | Format source |
|---|---|---|---|---|
| **NYC TLC Yellow Taxi** | 1 ligne = 1 course (dates, distance, montants, zones, paiement) | **~3 M lignes / mois** (≈ 40 M/an) | Mensuelle | Parquet |
| **Taxi Zone Lookup** | Référentiel `LocationID → Borough, Zone` | 265 lignes | Rare | CSV |
| **Open-Meteo (météo NYC)** | Température & précipitations par jour | ~365 lignes/an | Quotidienne | API JSON |

- Source officielle TLC : `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet`
- Météo : `https://archive-api.open-meteo.com/v1/archive` (gratuit, sans clé)

## Justification du choix (critères du cahier des charges)
- **Volume ≥ 1 M** : largement dépassé (un seul mois ≈ 3 M lignes ; **2 964 624** mesurées sur 2024-01).
- **Données temporelles / partitionnables** : horodatage à la course → partitionnement `year/month`.
- **≥ 2-3 tables joinables** : courses ⋈ zones (PU/DO) et courses ⋈ météo (par date).
- **Enjeux métier identifiables** : volumes par zone, revenus, pourboires, anomalies tarifaires, prévision.
- **Fraîcheur** : nouveau fichier mensuel → démonstration de l'**ingestion incrémentale** (1 mois = 1 partition).

## Note sur la donnée (cas de nettoyage volontairement présents)
Les données TLC **ne sont pas parfaites** (idéal pour la couche silver) : courses à distance
nulle ou négative, montants négatifs, `dropoff` antérieur au `pickup`, durées aberrantes
(> 4 h), nombres de passagers nuls. ~**8 %** des lignes sont filtrées en silver
(2 964 624 → 2 717 423 sur 2024-01). Voir [04_formats_stockage.md] et le SQL
`transformations/sql/silver_trips.sql`.

> **RGPD** : les données TLC récentes n'exposent plus de GPS précis (seulement des `LocationID` =
> zones, donc déjà généralisées). Pour **démontrer** la pseudonymisation, on ajoute à l'ingestion un
> champ **synthétique** `driver_email` (PII fictive), haché en `driver_pseudo` dès la couche silver.
> Détails dans [08_rgpd.md].
