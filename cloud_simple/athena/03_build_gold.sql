-- ===========================================================================
-- ÉTAPE 3 — Construire les DATAMARTS GOLD dans le cloud (Athena)
-- ---------------------------------------------------------------------------
-- 2 datamarts agrégés, prêts pour le dashboard / l'API. k-anonymat (k>=5) appliqué
-- (RGPD : on n'expose pas de maille représentant moins de 5 courses).
--
-- ⚠️ Pour relancer : DROP TABLE IF EXISTS ... ; et vider le dossier S3 correspondant.
-- ===========================================================================

-- --- Datamart 1 : demande & revenus par zone × heure × jour -----------------
CREATE TABLE nyc_taxi.demand_by_zone_hour
WITH (format = 'PARQUET', external_location = 's3://VOTRE-BUCKET/gold/demand_by_zone_hour/') AS
SELECT
    pu_borough,
    pu_zone,
    pickup_hour,
    pickup_dow_iso,
    COUNT(*)                          AS trips,
    ROUND(SUM(total_amount), 2)       AS revenue_total,
    ROUND(AVG(total_amount), 2)       AS avg_ticket,
    ROUND(AVG(trip_distance), 2)      AS avg_distance_mi,
    ROUND(AVG(trip_duration_min), 1)  AS avg_duration_min
FROM nyc_taxi.silver_trips
WHERE pu_borough IS NOT NULL
GROUP BY pu_borough, pu_zone, pickup_hour, pickup_dow_iso
HAVING COUNT(*) >= 5;

-- --- Datamart 2 : analyse des pourboires ------------------------------------
CREATE TABLE nyc_taxi.tips_analysis
WITH (format = 'PARQUET', external_location = 's3://VOTRE-BUCKET/gold/tips_analysis/') AS
SELECT
    pu_borough,
    payment_type,
    is_rush_hour,
    CASE WHEN precip_mm > 0 THEN TRUE ELSE FALSE END AS is_rainy,
    COUNT(*)                     AS trips,
    ROUND(AVG(tip_pct), 2)       AS avg_tip_pct,
    ROUND(AVG(tip_amount), 2)    AS avg_tip_amount,
    ROUND(AVG(total_amount), 2)  AS avg_ticket
FROM nyc_taxi.silver_trips
WHERE tip_pct IS NOT NULL AND pu_borough IS NOT NULL
GROUP BY pu_borough, payment_type, is_rush_hour,
         CASE WHEN precip_mm > 0 THEN TRUE ELSE FALSE END
HAVING COUNT(*) >= 5;

-- --- (Optionnel) Table des prédictions ML calculées en local et uploadées ----
-- À exécuter seulement si tu as uploadé ./data/gold/ml_predictions vers S3.
CREATE EXTERNAL TABLE IF NOT EXISTS nyc_taxi.ml_predictions (
  pickup_date     string,
  pu_zone         string,
  pu_borough      string,
  actual_total    double,
  predicted_total double,
  abs_error       double,
  is_anomaly      bigint
)
STORED AS PARQUET
LOCATION 's3://VOTRE-BUCKET/gold/ml_predictions/';
