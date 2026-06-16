-- ===========================================================================
-- ÉTAPE 4 — Requêtes d'exploration (réponses aux problématiques + captures)
-- Exécute-les dans la console Athena : chaque résultat = une capture pour le rapport.
-- Note à chaque requête le "Data scanned" affiché par Athena (indicateur de coût).
-- ===========================================================================

-- Problématique 1 — Top 10 zones par revenu
SELECT pu_borough, pu_zone, SUM(trips) AS trips, ROUND(SUM(revenue_total), 0) AS revenu
FROM nyc_taxi.demand_by_zone_hour
GROUP BY pu_borough, pu_zone
ORDER BY revenu DESC
LIMIT 10;

-- Problématique 1 — Heures les plus actives
SELECT pickup_hour, SUM(trips) AS courses
FROM nyc_taxi.demand_by_zone_hour
GROUP BY pickup_hour
ORDER BY courses DESC
LIMIT 5;

-- Problématique 2 — Pourboire moyen par mode de paiement (1=carte, 2=espèces)
SELECT payment_type, ROUND(AVG(avg_tip_pct), 1) AS pourboire_pct, SUM(trips) AS courses
FROM nyc_taxi.tips_analysis
GROUP BY payment_type
ORDER BY courses DESC;

-- Problématique 3 — Anomalies tarifaires détectées (si table ml_predictions créée)
SELECT pu_borough, pu_zone, actual_total, predicted_total, abs_error
FROM nyc_taxi.ml_predictions
WHERE is_anomaly = 1
ORDER BY abs_error DESC
LIMIT 20;
