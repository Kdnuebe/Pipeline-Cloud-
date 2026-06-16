# 2. Problématiques métier & KPI

Trois problématiques orientées **datamarts**, chacune adossée à une table gold et exposée
via l'API et le dashboard.

## Problématique 1 — Où et quand la demande et les revenus sont-ils les plus forts ?
*Datamart : `gold.demand_by_zone_hour`*

| KPI | Définition |
|---|---|
| `trips` | Nombre de courses par zone × heure × jour |
| `revenue_total` | Somme des montants encaissés |
| `avg_ticket` | Montant moyen par course |
| `avg_distance_mi` | Distance moyenne (miles) |
| `avg_duration_min` | Durée moyenne (minutes) |

**Usage** : identifier les zones/créneaux à prioriser (affectation des chauffeurs, tarification).

## Problématique 2 — Quels facteurs influencent le pourboire ?
*Datamart : `gold.tips_analysis`*

| KPI | Définition |
|---|---|
| `avg_tip_pct` | Taux de pourboire moyen (% du tarif) |
| `avg_tip_amount` | Pourboire moyen (USD) |
| segments | arrondissement × mode de paiement × heure de pointe × météo (pluie) |

**Usage** : comprendre le comportement de pourboire (ex. carte vs espèces, météo).

## Problématique 3 (ML, bonus) — Peut-on prédire le montant d'une course et repérer les anomalies ?
*Datamart : `gold.ml_predictions`*

| KPI | Définition |
|---|---|
| `predicted_total` | Montant prédit par le modèle (RandomForest) |
| `abs_error` | Écart absolu réel/prédit |
| `is_anomaly` | Course tarifaire atypique (IsolationForest) |
| métriques | MAE, RMSE, R² comparés à une baseline |

**Usage** : estimation de prix, détection de fraude/erreurs de facturation.

> Les réponses chiffrées (résultats réels mesurés) sont en [09_interpretations_metier.md].
